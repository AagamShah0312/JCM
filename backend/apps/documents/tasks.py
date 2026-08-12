"""
Celery tasks for the document processing pipeline (spec §6, §37).

Each task is idempotent-ish and updates the document's processing_state;
a failure never corrupts the original file (we only record the error).
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_document_task(self, document_id: str):
    """
    Full document pipeline: extract text → OCR if needed → chunk → store
    extraction → store chunks → generate embeddings → mark PROCESSED.
    """
    from apps.documents.models import (
        CaseDocument, DocumentExtraction, DocumentChunk, DocumentProcessingState,
    )
    from apps.documents.pipeline import process_document_content
    from apps.documents.services import generate_and_store_embeddings

    doc = CaseDocument.objects.filter(id=document_id).first()
    if not doc:
        logger.warning(f"process_document_task: document {document_id} not found")
        return {'error': 'document not found'}

    try:
        doc.processing_state = DocumentProcessingState.PROCESSING
        doc.save(update_fields=['processing_state', 'updated_at'])

        result = process_document_content(doc)
        if result.get('error'):
            raise RuntimeError(result['error'])

        full_text = result.get('full_text', '')
        pages = result.get('pages', [])
        chunks = result.get('chunks', [])
        ocr_used = result.get('ocr_used', False)

        # Store extraction (page-level metadata preserved)
        DocumentExtraction.objects.update_or_create(
            document=doc,
            defaults={
                'extracted_text': full_text,
                'ocr_text': full_text if ocr_used else '',
                'page_metadata': {'pages': pages, 'ocr_used': ocr_used},
                'metadata': {'source': 'pipeline', 'ocr_used': ocr_used},
            },
        )

        # Store chunks
        DocumentChunk.objects.filter(document=doc).delete()
        chunk_objs = []
        for chunk in chunks:
            chunk_objs.append(DocumentChunk(
                document=doc,
                case=doc.case,
                hearing=doc.hearing,
                chunk_index=chunk['index'],
                page_number=chunk.get('page'),
                text=chunk['text'],
                collection='case_documents',
                embedding_model='',
                document_version=doc.versions.count() + 1 if doc.versions.exists() else 1,
                visibility=doc.visibility,
            ))
        DocumentChunk.objects.bulk_create(chunk_objs)

        doc.processing_state = (
            DocumentProcessingState.OCR_COMPLETED if ocr_used
            else DocumentProcessingState.PROCESSED
        )
        doc.processing_error = ''
        doc.save(update_fields=['processing_state', 'processing_error', 'updated_at'])

        # Embeddings (may be async in the same task; failures recorded but not fatal)
        try:
            generate_and_store_embeddings(document_id)
        except Exception as exc:
            logger.warning(f"Embedding generation failed for {document_id}: {exc}")

        return {
            'document_id': str(doc.id),
            'state': doc.processing_state,
            'chunks': len(chunk_objs),
            'chars': len(full_text),
            'ocr_used': ocr_used,
        }
    except Exception as exc:
        logger.exception(f"process_document_task failed for {document_id}")
        doc.processing_state = DocumentProcessingState.FAILED
        doc.processing_error = str(exc)[:2000]
        doc.save(update_fields=['processing_state', 'processing_error', 'updated_at'])
        try:
            raise self.retry(exc=exc)
        except Exception as retry_exc:
            # Max retries reached — surface the failure state.
            return {'error': str(exc)}


@shared_task(bind=True, max_retries=2)
def generate_embeddings_task(self, document_id: str):
    """Generate + store pgvector embeddings for a document's chunks."""
    from apps.documents.services import generate_and_store_embeddings

    try:
        return generate_and_store_embeddings(document_id)
    except Exception as exc:
        logger.exception(f"generate_embeddings_task failed for {document_id}")
        raise self.retry(exc=exc)


@shared_task
def reprocess_document_task(document_id: str):
    """Re-run the pipeline (e.g. after fixing OCR or when new data arrives)."""
    return process_document_task.delay(document_id).get(timeout=300)
