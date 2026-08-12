"""
Document services: embedding generation + pgvector storage.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_and_store_embeddings(document_id: str, model: str = None) -> dict:
    """
    Generate embeddings for all chunks of a document and store them in
    pgvector. Uses the configured AI embedding provider.
    """
    from apps.documents.models import CaseDocument, DocumentChunk
    from apps.ai.embeddings import embed_texts, get_embedding_dimension

    doc = CaseDocument.objects.filter(id=document_id).first()
    if not doc:
        return {'error': 'document not found'}

    chunks = list(DocumentChunk.objects.filter(document=doc).order_by('chunk_index'))
    if not chunks:
        return {'chunks': 0}

    model = model or settings.AI_EMBEDDING_MODEL
    try:
        vectors = embed_texts([c.text for c in chunks], model=model)
    except Exception as exc:
        logger.error(f"embed_texts failed for {document_id}: {exc}")
        raise

    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = list(vector)
        chunk.embedding_model = model
        chunk.save(update_fields=['embedding', 'embedding_model'])

    return {'document_id': str(doc.id), 'chunks': len(chunks), 'model': model, 'dim': get_embedding_dimension()}
