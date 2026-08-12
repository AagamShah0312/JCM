"""
Document processing pipeline: extraction, OCR, chunking, indexing.

Implements spec §6 and §37:
  upload → validate → store original → process → extract text → OCR if
  necessary → normalize → chunk → store chunks → generate embeddings →
  store vector representation → index

Processing is async (Celery). A failure must NOT corrupt the original
document; we only update the processing_state + error message.
"""
import hashlib
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

# Chunking defaults
DEFAULT_CHUNK_SIZE = 1200          # chars
DEFAULT_CHUNK_OVERLAP = 150        # chars


class DocumentPipelineError(Exception):
    pass


def compute_checksum(file_path: str) -> str:
    """SHA-256 of a file on disk."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def detect_meaningful_text(text: str, min_chars: int = 40) -> bool:
    """Heuristic: does the extracted text contain meaningful content?"""
    stripped = ' '.join((text or '').split())
    return len(stripped) >= min_chars


def extract_text_pdf(file_path: str) -> dict:
    """
    Extract text from a PDF using PyMuPDF (pymupdf). Returns:
    {
      'full_text': str,
      'pages': [{'page': int, 'text': str}],
      'needs_ocr': bool  # pages with little/no extractable text
    }
    """
    import pymupdf

    doc = pymupdf.open(file_path)
    pages = []
    full_parts = []
    needs_ocr = False
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ''
        pages.append({'page': i, 'text': text})
        if text.strip():
            full_parts.append(text)
        else:
            needs_ocr = True
    doc.close()
    full_text = '\n'.join(part for part in full_parts if part.strip())
    return {
        'full_text': full_text,
        'pages': pages,
        'needs_ocr': needs_ocr,
    }


def render_page_to_image(file_path: str, page_number: int, dpi: int = 200) -> str:
    """Render a PDF page to a PNG temp file for OCR."""
    import pymupdf

    doc = pymupdf.open(file_path)
    page = doc.load_page(page_number - 1)
    pix = page.get_pixmap(dpi=dpi)
    out_path = f"/tmp/jcm_ocr_{hashlib.md5(file_path.encode()).hexdigest()}_{page_number}.png"
    pix.save(out_path)
    doc.close()
    return out_path


def preprocess_image(image_path: str) -> str:
    """
    Preprocess an image with OpenCV before OCR: grayscale, denoise,
    adaptive threshold. Returns path to the preprocessed image.
    """
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return image_path
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    # Upscale small images a bit for better OCR
    if gray.shape[0] < 600:
        scale = 600 / gray.shape[0]
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out_path = image_path.replace('.png', '_proc.png')
    cv2.imwrite(out_path, thresh)
    return out_path


def ocr_image(image_path: str, lang: str = 'eng') -> str:
    """Run Tesseract OCR on an image."""
    import pytesseract
    return pytesseract.image_to_string(image_path, lang=lang)


def ocr_pdf(file_path: str) -> dict:
    """
    OCR an entire PDF page by page. Returns {'full_text', 'pages', 'needs_ocr'}.
    """
    import pymupdf

    doc = pymupdf.open(file_path)
    pages = []
    full_parts = []
    for i, page in enumerate(doc, start=1):
        rendered = render_page_to_image(file_path, i)
        processed = preprocess_image(rendered)
        try:
            text = ocr_image(processed)
        finally:
            # Clean up temp images (never the original document file).
            for tmp in (rendered, processed):
                try:
                    if os.path.abspath(tmp) != os.path.abspath(file_path):
                        os.remove(tmp)
                except OSError:
                    pass
        pages.append({'page': i, 'text': text})
        if text.strip():
            full_parts.append(text)
    doc.close()
    return {
        'full_text': '\n'.join(part for part in full_parts if part.strip()),
        'pages': pages,
        'needs_ocr': False,
    }


def extract_text(file_path: str, mime_hint: str = '') -> dict:
    """Extract text from a file based on its extension/mime."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        result = extract_text_pdf(file_path)
        if not detect_meaningful_text(result['full_text']) or result['needs_ocr']:
            # Scanned PDF: OCR page by page
            logger.info(f"PDF {file_path} has little text — running OCR")
            try:
                ocr_result = ocr_pdf(file_path)
                if detect_meaningful_text(ocr_result['full_text']):
                    result = ocr_result
                    result['ocr_used'] = True
            except Exception as exc:
                logger.error(f"OCR failed for {file_path}: {exc}")
                result['ocr_error'] = str(exc)
        result.setdefault('ocr_used', False)
        return result
    elif ext in ('.docx', '.doc'):
        from docx import Document
        doc = Document(file_path)
        text = '\n'.join(p.text for p in doc.paragraphs)
        return {'full_text': text, 'pages': [{'page': 1, 'text': text}], 'needs_ocr': False}
    elif ext == '.txt':
        for encoding in ('utf-8', 'utf-16', 'latin-1'):
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                return {'full_text': text, 'pages': [{'page': 1, 'text': text}], 'needs_ocr': False}
            except UnicodeDecodeError:
                continue
        return {'full_text': '', 'pages': [], 'needs_ocr': False}
    elif ext in ('.jpg', '.jpeg', '.png'):
        processed = preprocess_image(file_path)
        try:
            text = ocr_image(processed)
        finally:
            try:
                if os.path.abspath(processed) != os.path.abspath(file_path):
                    os.remove(processed)
            except OSError:
                pass
        return {'full_text': text, 'pages': [{'page': 1, 'text': text}], 'needs_ocr': False}
    return {'full_text': '', 'pages': [], 'needs_ocr': False}


def chunk_text(full_text: str, chunk_size: int = None, overlap: int = None) -> list:
    """
    Split text into overlapping chunks for retrieval. Returns a list of
    {'index', 'text', 'page'} dicts where page is best-effort (approximated
    by character position if pages are not provided).
    """
    chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
    overlap = overlap or DEFAULT_CHUNK_OVERLAP
    text = full_text or ''
    text = ' '.join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({'index': idx, 'text': chunk, 'page': None})
            idx += 1
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def chunk_text_with_pages(pages: list, chunk_size: int = None, overlap: int = None) -> list:
    """
    Chunk page-aware text so citations can point to the correct page (§33, §37).
    pages: [{'page': int, 'text': str}]
    """
    chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
    overlap = overlap or DEFAULT_CHUNK_OVERLAP
    chunks = []
    for page_info in pages:
        page_text = ' '.join((page_info.get('text') or '').split())
        if not page_text:
            continue
        start = 0
        while start < len(page_text):
            end = min(start + chunk_size, len(page_text))
            chunk_text = page_text[start:end]
            if chunk_text.strip():
                chunks.append({
                    'index': len(chunks),
                    'text': chunk_text,
                    'page': page_info['page'],
                })
            if end >= len(page_text):
                break
            start = end - overlap
    return chunks


def process_document_content(doc) -> dict:
    """
    Full processing for a CaseDocument: extract → OCR if needed → chunk.
    Returns a dict with 'full_text', 'pages', 'chunks', 'ocr_used', 'error'.
    Does NOT touch embeddings (handled by a separate task).
    """
    from apps.documents.models import DocumentProcessingState

    if not doc.file:
        return {'error': 'Document has no file'}

    try:
        file_path = doc.file.path
    except Exception as exc:
        return {'error': f'Cannot resolve file path: {exc}'}

    if not os.path.exists(file_path):
        return {'error': 'File not found on storage'}

    try:
        result = extract_text(file_path, doc.mime_type)
        chunks = chunk_text_with_pages(result.get('pages') or [{'page': 1, 'text': result.get('full_text', '')}])
        result['chunks'] = chunks
        return result
    except Exception as exc:
        logger.exception(f"Document processing failed for {doc.id}")
        return {'error': str(exc)}
