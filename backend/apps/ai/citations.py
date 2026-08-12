"""
Citation builder for AI answers (spec §33).

Every factual AI answer should reference sources. The UI renders citations
as clickable links to the relevant case/hearing/proceeding/document/order.
"""
import logging

from django.urls import reverse

logger = logging.getLogger(__name__)


def build_document_citation(chunk, document):
    """Citation for a document chunk (with page number where available)."""
    return {
        'source_type': 'chunk',
        'source_id': str(chunk.id),
        'source_label': f"{document.file_name}" + (f" — p.{chunk.page_number}" if chunk.page_number else ''),
        'page_number': chunk.page_number,
        'chunk_index': chunk.chunk_index,
        'excerpt': (chunk.text or '')[:300],
        'url': '',
        'metadata': {
            'document_id': str(document.id),
            'case_id': str(document.case_id),
            'document_type': document.document_type,
        },
    }


def build_hearing_citation(hearing):
    return {
        'source_type': 'hearing',
        'source_id': str(hearing.id),
        'source_label': f"Hearing #{hearing.hearing_number} — {hearing.date.isoformat() if hearing.date else ''}",
        'page_number': None,
        'chunk_index': None,
        'excerpt': hearing.purpose or hearing.adjournment_note or '',
        'url': '',
        'metadata': {'case_id': str(hearing.case_id), 'status': hearing.status},
    }


def build_proceeding_citation(proceeding):
    return {
        'source_type': 'proceeding',
        'source_id': str(proceeding.id),
        'source_label': f"Proceedings — Hearing #{proceeding.hearing.hearing_number}",
        'page_number': None,
        'chunk_index': None,
        'excerpt': (proceeding.summary or '')[:300],
        'url': '',
        'metadata': {
            'case_id': str(proceeding.hearing.case_id),
            'hearing_id': str(proceeding.hearing_id),
        },
    }


def build_order_citation(order):
    return {
        'source_type': 'order',
        'source_id': str(order.id),
        'source_label': f"Order — {order.title} ({order.date.isoformat() if order.date else ''})",
        'page_number': None,
        'chunk_index': None,
        'excerpt': (order.summary or '')[:300],
        'url': '',
        'metadata': {'case_id': str(order.case_id), 'status': order.status},
    }


def build_case_citation(case):
    return {
        'source_type': 'case',
        'source_id': str(case.id),
        'source_label': f"Case {case.case_number} — {case.title}",
        'page_number': None,
        'chunk_index': None,
        'excerpt': (case.description or '')[:300],
        'url': '',
        'metadata': {'status': case.status},
    }


def serialize_context_citations(context):
    """
    Convert a retrieval context (see apps.ai.retrieval.retrieve_case_context)
    into a flat list of citation dicts (deduplicated by source label).
    """
    citations = []
    seen = set()

    for chunk_item in context.get('chunks', []):
        cit = build_document_citation(chunk_item['chunk'], chunk_item['document'])
        key = cit['source_label']
        if key not in seen:
            citations.append(cit)
            seen.add(key)

    for h in context.get('hearings', []):
        # h is already a dict from retrieval; rebuild label for dedupe
        label = f"Hearing #{h['number']} — {h.get('date') or ''}"
        if label not in seen:
            citations.append({
                'source_type': 'hearing',
                'source_id': h['id'],
                'source_label': label,
                'page_number': None,
                'chunk_index': None,
                'excerpt': h.get('purpose') or h.get('adjournment_reason') or '',
                'url': '',
                'metadata': {'case_id': '', 'status': h.get('status')},
            })
            seen.add(label)

    for p in context.get('proceedings', []):
        label = f"Proceedings — {p.get('hearing', '')}"
        if label not in seen:
            citations.append({
                'source_type': 'proceeding',
                'source_id': p['id'],
                'source_label': label,
                'page_number': None,
                'chunk_index': None,
                'excerpt': (p.get('summary') or '')[:300],
                'url': '',
                'metadata': {'hearing_id': p.get('hearing', '')},
            })
            seen.add(label)

    for o in context.get('orders', []):
        label = f"Order — {o.get('title', '')} ({o.get('date') or ''})"
        if label not in seen:
            citations.append({
                'source_type': 'order',
                'source_id': o['id'],
                'source_label': label,
                'page_number': None,
                'chunk_index': None,
                'excerpt': (o.get('summary') or '')[:300],
                'url': '',
                'metadata': {'status': o.get('status')},
            })
            seen.add(label)

    return citations
