"""
Permission-filtered retrieval for the Case AI (spec §34, §72).

CRITICAL: authorization happens BEFORE retrieval. The user can only ever
receive content from cases/documents they are allowed to see. Vector search
runs only over the already-authorized chunk set.
"""
import logging

from django.conf import settings
from django.db.models import Q

from apps.ai.embeddings import embed_texts
from apps.cases.permissions import can_view_case, can_view_document

logger = logging.getLogger(__name__)

MAX_CHUNKS_RETRIEVED = 8


def authorized_document_ids(user, case):
    """All document IDs the user may retrieve within this case."""
    from apps.documents.models import CaseDocument
    qs = CaseDocument.objects.filter(case=case, state='ACTIVE')
    allowed = []
    for doc in qs:
        if can_view_document(user, doc):
            allowed.append(doc.id)
    return allowed


def retrieve_for_query(user, case, query, top_k=MAX_CHUNKS_RETRIEVED):
    """
    Retrieve relevant chunks for a query, filtered by authorization first.

    Returns a list of dicts:
      {chunk, document, page_number, chunk_index, text, score}
    """
    from apps.documents.models import DocumentChunk

    if not can_view_case(user, case):
        return []

    doc_ids = authorized_document_ids(user, case)
    if not doc_ids:
        return []

    # 1) Candidate pool = chunks of authorized documents only.
    candidate_qs = DocumentChunk.objects.filter(
        document_id__in=doc_ids,
        document__state='ACTIVE',
        collection='case_documents',
    ).select_related('document', 'case')

    # 2) Embedding-based search when possible (pgvector similarity).
    try:
        query_vec = embed_texts([query])[0] if query.strip() else None
        if query_vec:
            from pgvector.django import CosineDistance, Vector
            scored = (
                candidate_qs.filter(embedding__isnull=False)
                .annotate(distance=CosineDistance('embedding', Vector(query_vec)))
                .order_by('distance')[:top_k]
            )
            results = []
            for chunk in scored:
                results.append({
                    'chunk': chunk,
                    'document': chunk.document,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    'text': chunk.text,
                    'score': max(0.0, 1.0 - float(chunk.distance)),
                })
            return results
    except Exception as exc:
        logger.warning(f"Vector retrieval failed ({exc}); falling back to keyword")

    # 3) Keyword fallback (pg_trgm / icontains) — no embedding required.
    terms = [t for t in query.lower().split() if len(t) > 2]
    q_filter = Q()
    for term in terms:
        q_filter |= Q(text__icontains=term)
    if not terms:
        q_filter = Q()  # empty query -> most recent chunks
    fallback = list(candidate_qs.filter(q_filter).order_by('-created_at')[:top_k])
    return [{
        'chunk': chunk,
        'document': chunk.document,
        'page_number': chunk.page_number,
        'chunk_index': chunk.chunk_index,
        'text': chunk.text,
        'score': None,
    } for chunk in fallback]


def retrieve_case_context(user, case, query, top_k=MAX_CHUNKS_RETRIEVED):
    """Full context bundle for the AI: authorized chunks + case/hearing/order facts."""
    from apps.hearings.models import Hearing, HearingProceeding
    from apps.orders.models import Order

    chunks = retrieve_for_query(user, case, query, top_k=top_k)

    # Authorized hearings/proceedings/orders (case-scoped; user already can view case).
    hearings = Hearing.objects.filter(case=case).order_by('-date')[:10]
    proceedings = HearingProceeding.objects.filter(hearing__case=case).order_by('-created_at')[:10]
    orders = Order.objects.filter(case=case).exclude(status='DRAFT').order_by('-date')[:10]

    return {
        'chunks': chunks,
        'hearings': [
            {'id': str(h.id), 'number': h.hearing_number, 'date': h.date.isoformat() if h.date else None,
             'status': h.status, 'purpose': h.purpose,
             'adjournment_reason': h.adjournment_reason.code if h.adjournment_reason else None}
            for h in hearings
        ],
        'proceedings': [
            {'id': str(p.id), 'hearing': str(p.hearing_id), 'summary': p.summary[:1500],
             'next_hearing_date': p.next_hearing_date.isoformat() if p.next_hearing_date else None,
             'is_public': p.is_public}
            for p in proceedings
        ],
        'orders': [
            {'id': str(o.id), 'title': o.title, 'date': o.date.isoformat() if o.date else None,
             'status': o.status, 'summary': o.summary[:1500]}
            for o in orders
        ],
    }
