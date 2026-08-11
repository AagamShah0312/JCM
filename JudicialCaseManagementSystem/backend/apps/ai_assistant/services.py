"""
AI services for case-aware prompts and document processing.
"""
import os
import logging
from typing import List, Dict, Any, Iterable

from django.conf import settings

from apps.cases.models import Case
from apps.documents.models import CaseDocument
from services.ai_service import ask_gemini

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents for AI analysis"""
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from document"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                return DocumentProcessor._extract_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                return DocumentProcessor._extract_docx(file_path)
            elif ext in ['.txt']:
                return DocumentProcessor._extract_txt(file_path)
            elif ext in ['.jpg', '.jpeg', '.png']:
                return DocumentProcessor._extract_image(file_path)
            else:
                return ""
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""
    
    @staticmethod
    def _extract_pdf(file_path: str) -> str:
        """Extract text from PDF"""
        try:
            import pdfplumber
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or '')
            return '\n'.join(part for part in text if part)
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            return ""

    @staticmethod
    def _extract_txt(file_path: str) -> str:
        """Extract text from plain text files with common encodings."""
        for encoding in ('utf-8', 'utf-16', 'latin-1'):
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""
    
    @staticmethod
    def _extract_docx(file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error extracting DOCX: {str(e)}")
            return ""

    @staticmethod
    def _extract_image(file_path: str) -> str:
        """Extract text from images when OCR dependencies are available."""
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            logger.error(f"Error extracting image text: {str(e)}")
            return ""


class RAGService:
    """Retrieval-Augmented Generation service backed by Google Gemini."""

    def __init__(self):
        self.use_local_llm = settings.USE_LOCAL_LLM
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.openai_api_key = settings.OPENAI_API_KEY

    def _call_llm(self, prompt: str, model: str | None = None) -> str:
        try:
            return (ask_gemini(prompt, model=model) or "").strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "[LLM error] Unable to produce response"

    def _case_summary(self, case: Case) -> Dict[str, Any]:
        return {
            'id': str(case.id),
            'case_number': case.case_number,
            'title': case.title,
            'description': case.description,
            'status': case.status,
            'status_label': case.get_status_display(),
            'court_name': case.court_name,
            'case_type': case.case_type,
            'filing_date': case.filing_date.isoformat() if case.filing_date else None,
            'next_hearing_date': case.next_hearing_date.isoformat() if case.next_hearing_date else None,
            'judge_name': case.judge_name or '',
            'plaintiff_name': case.plaintiff_name,
            'defendant_name': case.defendant_name,
        }

    def _gather_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Collect extracted texts for a case."""
        from apps.documents.models import DocumentExtraction

        docs = CaseDocument.objects.filter(case_id=case_id).select_related('extraction').order_by('-uploaded_at')
        results = []
        for d in docs:
            text = ''
            try:
                extraction = d.extraction
                text = extraction.extracted_text or extraction.ocr_text or ''
            except Exception:
                text = ''
            if not text and d.file:
                try:
                    text = DocumentProcessor.extract_text(d.file.path)
                    DocumentExtraction.objects.update_or_create(
                        document=d,
                        defaults={
                            'extracted_text': text,
                            'ocr_text': '',
                            'metadata': {'source': 'ai_lazy_extract'},
                        },
                    )
                except Exception as exc:
                    logger.warning(f"Lazy extraction failed for document {d.id}: {exc}")
            if not text and d.file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                text = 'Image document uploaded. OCR text is empty or OCR engine is unavailable.'
            snippet = ' '.join((text or d.description or '').split())
            results.append({
                'id': str(d.id),
                'file_name': d.file_name,
                'document_type': d.document_type,
                'description': d.description or '',
                'text': snippet[:5000],
                'uploaded_at': d.uploaded_at.isoformat() if d.uploaded_at else None,
                'file_url': getattr(d.file, 'url', ''),
            })
        return results

    def _pick_relevant_documents(self, query: str, documents: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        if not documents:
            return []

        corpus = [
            f"{doc['file_name']} {doc['document_type']} {doc['description']} {doc['text']}".strip()
            for doc in documents
        ]

        indices: Iterable[int]
        try:
            if query.strip():
                hits = EmbeddingService.semantic_search(query, corpus, top_k=min(top_k, len(corpus)))
                indices = [int(hit['corpus_id']) for hit in hits] if hits else range(min(top_k, len(documents)))
            else:
                indices = range(min(top_k, len(documents)))
        except Exception:
            indices = range(min(top_k, len(documents)))

        selected = []
        for idx in indices:
            try:
                selected.append(documents[int(idx)])
            except Exception:
                continue
        return selected[:top_k]

    def _build_case_prompt(
        self,
        case: Case,
        query: str,
        documents: List[Dict[str, Any]],
        history: List[Dict[str, str]] | None = None,
        mode: str = 'chat',
    ) -> str:
        history_lines = []
        if history:
            for message in history[-10:]:
                role = (message.get('role') or 'user').strip().capitalize()
                content = (message.get('content') or '').strip()
                if content:
                    history_lines.append(f"{role}: {content}")

        document_lines = []
        for index, doc in enumerate(documents, start=1):
            document_lines.append(
                f"{index}. {doc['file_name']} ({doc['document_type']})\n"
                f"   {doc['text'][:1500]}"
            )

        case_block = (
            f"Case Number: {case.case_number}\n"
            f"Case Title: {case.title}\n"
            f"Case Description: {case.description}\n"
            f"Status: {case.get_status_display()}\n"
            f"Court: {case.court_name}\n"
            f"Case Type: {case.case_type}\n"
            f"Filing Date: {case.filing_date.isoformat() if case.filing_date else 'N/A'}\n"
            f"Next Hearing Date: {case.next_hearing_date.isoformat() if case.next_hearing_date else 'N/A'}\n"
            f"Judge: {case.judge_name or 'N/A'}\n"
            f"Plaintiff: {case.plaintiff_name}\n"
            f"Defendant: {case.defendant_name}"
        )

        if mode == 'explain':
            instructions = (
                "Explain the case in simple, non-technical language for a non-lawyer. "
                "Keep the answer clean and practical. Use short sections: Overview, Parties, Status, Documents, Next Steps. "
                "Do not invent facts. If information is missing, say so clearly."
            )
        else:
            instructions = (
                "You are a legal case assistant inside a judicial case management system. "
                "Answer case questions from case details, selected documents, and conversation history. "
                "You may also answer general questions unrelated to the case like a normal AI assistant. "
                "Do not give a direct judicial opinion, verdict, or instruction on who should win. "
                "For legal strategy or case merits, give neutral educational context and cite document file names when relevant."
            )

        history_block = "\n".join(history_lines) if history_lines else "No prior conversation."
        documents_block = "\n\n".join(document_lines) if document_lines else "No relevant documents were found."

        return (
            f"{instructions}\n\n"
            f"CASE DETAILS\n{case_block}\n\n"
            f"CONVERSATION HISTORY\n{history_block}\n\n"
            f"RELEVANT DOCUMENTS\n{documents_block}\n\n"
            f"USER REQUEST\n{query}\n\n"
            "Return a direct answer in plain language."
        )

    def query_case(self, case_id: str, query: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
        """Query a case using case details, document excerpts, and optional conversation history."""
        try:
            case = Case.objects.get(id=case_id)
            docs = self._gather_documents(case_id)
            selected_docs = self._pick_relevant_documents(query, docs)
            prompt = self._build_case_prompt(case, query, selected_docs, history=history, mode='chat')

            answer = self._call_llm(prompt)
            sources = [
                {'doc_id': doc['id'], 'file_name': doc['file_name'], 'document_type': doc['document_type']}
                for doc in selected_docs
            ]
            return {
                'success': True,
                'response': answer,
                'sources': sources,
                'tokens_used': 0,
                'case': self._case_summary(case),
            }
        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}")
            return {'success': False, 'error': str(e), 'response': 'Unable to process query'}

    def explain_case(self, case_id: str) -> Dict[str, Any]:
        """Generate a simplified explanation for a case."""
        try:
            case = Case.objects.get(id=case_id)
            docs = self._gather_documents(case_id)
            selected_docs = self._pick_relevant_documents(case.description or case.title, docs)
            prompt = self._build_case_prompt(case, 'Explain this case in simple language.', selected_docs, mode='explain')
            explanation = self._call_llm(prompt)
            sources = [
                {'doc_id': doc['id'], 'file_name': doc['file_name'], 'document_type': doc['document_type']}
                for doc in selected_docs
            ]
            return {
                'success': True,
                'explanation': explanation,
                'sources': sources,
                'case': self._case_summary(case),
                'tokens_used': 0,
            }
        except Exception as e:
            logger.error(f"Error explaining case: {str(e)}")
            return {'success': False, 'error': str(e)}

    def summarize_case(self, case_id: str) -> Dict[str, Any]:
        """Generate a concise summary of the case by aggregating top documents and asking the LLM to summarize."""
        try:
            case = Case.objects.get(id=case_id)
            docs = self._gather_documents(case_id)
            selected_docs = self._pick_relevant_documents(case.description or case.title, docs)
            context = self._build_case_prompt(case, 'Summarize the case for internal review.', selected_docs, mode='chat')
            prompt = (
                "Summarize the case in 6-8 bullet points. Highlight the parties, case status, major facts, "
                "document references, and what a user should look at next.\n\n"
                f"{context}"
            )
            summary = self._call_llm(prompt)
            return {'success': True, 'summary': summary, 'tokens_used': 0}
        except Exception as e:
            logger.error(f"Error summarizing case: {str(e)}")
            return {'success': False, 'error': str(e)}

    def generate_timeline(self, case_id: str) -> Dict[str, Any]:
        """Generate a timeline (date-ordered) of events extracted from documents using the LLM."""
        try:
            case = Case.objects.get(id=case_id)
            docs = self._gather_documents(case_id)
            selected_docs = self._pick_relevant_documents(case.description or case.title, docs)
            combined = self._build_case_prompt(case, 'Extract a chronological timeline from the case documents.', selected_docs, mode='chat')
            prompt = (
                "Extract a chronological timeline of events from the documents below. "
                "Return a JSON array of {date: 'YYYY-MM-DD', event: 'short title', description: 'details'}:\n\n" + combined
            )
            timeline_text = self._call_llm(prompt)
            # Do not attempt to fully parse; return raw timeline_text
            return {'success': True, 'timeline': timeline_text, 'tokens_used': 0}
        except Exception as e:
            logger.error(f"Error generating timeline: {str(e)}")
            return {'success': False, 'error': str(e)}


class EmbeddingService:
    """Service for document embeddings"""
    
    @staticmethod
    def generate_embeddings(text: str) -> List[float]:
        """Generate embeddings for text using sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = model.encode(text)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []
    
    @staticmethod
    def semantic_search(query: str, documents: List[str], top_k: int = 3) -> List[int]:
        """Find semantically similar documents"""
        try:
            from sentence_transformers import SentenceTransformer, util
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            query_embedding = model.encode(query, convert_to_tensor=True)
            doc_embeddings = model.encode(documents, convert_to_tensor=True)
            
            hits = util.semantic_search(query_embedding, doc_embeddings, top_k=top_k)
            return hits[0]
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
