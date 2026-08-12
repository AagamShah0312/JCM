"""
Case AI services: Q&A, summaries, citations (spec §31-§36).

Everything here is permission-filtered via apps.ai.retrieval BEFORE any LLM
call. Responses follow the structured shape:
  {answer, citations, sources, warnings, ...}
"""
import logging

from django.conf import settings

from apps.ai.citations import serialize_context_citations
from apps.ai.prompts import (
    build_qa_prompt, build_summary_prompt, build_change_summary_prompt,
    build_compare_prompt,
)
from apps.ai.providers import get_ai_provider, AIProviderError
from apps.ai.retrieval import retrieve_case_context, retrieve_for_query
from apps.cases.permissions import can_view_case

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "AI-generated assistance. Verify against source documents; this is advisory "
    "and not a judicial opinion."
)


def _call_provider(prompt, system=None):
    provider = get_ai_provider()
    return provider.chat(
        messages=[{'role': 'user', 'content': prompt}],
        system=system,
        temperature=settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
    )


def _not_configured_response():
    # success=True so the API returns 200 with a clear setup message instead
    # of erroring; not_configured flag lets callers surface a setup hint.
    return {
        'success': True,
        'not_configured': True,
        'answer': "[AI not configured] Add your GEMINI_API_KEY to the backend .env file to enable the AI assistant.",
        'summary': "[AI not configured] Add your GEMINI_API_KEY to the backend .env file to enable the AI assistant.",
        'citations': [],
        'sources': [],
        'warnings': [DISCLAIMER],
        'error': 'AI not configured',
    }


def answer_case_question(user, case, query, history=None):
    """Q&A over an authorized case. Returns structured answer + citations."""
    if not can_view_case(user, case):
        return {'success': False, 'error': 'Not authorized to this case', 'answer': ''}

    try:
        context = retrieve_case_context(user, case, query)
    except Exception as exc:
        logger.exception(f"Retrieval failed for case {case.id}")
        return {'success': False, 'error': f'Retrieval failed: {exc}', 'answer': ''}

    prompt = build_qa_prompt(case, query, context, history=history)
    try:
        answer = _call_provider(prompt)
    except AIProviderError as exc:
        if 'not configured' in str(exc).lower() or 'GEMINI_API_KEY' in str(exc):
            return _not_configured_response()
        return {'success': False, 'error': str(exc), 'answer': ''}

    citations = serialize_context_citations(context)
    return {
        'success': True,
        'answer': answer,
        'citations': citations,
        'sources': [{'doc_id': str(c['source_id']), 'label': c['source_label']} for c in citations],
        'warnings': [DISCLAIMER],
        'retrieved_chunks': len(context.get('chunks', [])),
    }


def summarize_case(user, case, summary_type='case'):
    """Case/hearing/document summary with citations."""
    if not can_view_case(user, case):
        return {'success': False, 'error': 'Not authorized to this case'}

    try:
        context = retrieve_case_context(user, case, case.title)
    except Exception as exc:
        logger.exception(f"Retrieval failed for case {case.id}")
        return {'success': False, 'error': str(exc)}

    prompt = build_summary_prompt(case, context, summary_type=summary_type)
    try:
        summary = _call_provider(prompt)
    except AIProviderError as exc:
        if 'not configured' in str(exc).lower() or 'GEMINI_API_KEY' in str(exc):
            return _not_configured_response()
        return {'success': False, 'error': str(exc)}

    return {
        'success': True,
        'summary': summary,
        'citations': serialize_context_citations(context),
        'warnings': [DISCLAIMER],
    }


def summarize_hearing(user, case, hearing):
    return summarize_case(user, case, summary_type='hearing')


def summarize_documents(user, case):
    return summarize_case(user, case, summary_type='document')


def what_changed_summary(user, case, changes):
    """AI summary of a 'What changed?' list (spec §39)."""
    if not changes:
        return {'success': True, 'summary': 'No changes detected since your last visit.', 'citations': []}
    if not can_view_case(user, case):
        return {'success': False, 'error': 'Not authorized to this case'}
    prompt = build_change_summary_prompt(case, changes)
    try:
        summary = _call_provider(prompt)
    except AIProviderError as exc:
        if 'not configured' in str(exc).lower() or 'GEMINI_API_KEY' in str(exc):
            return _not_configured_response()
        return {'success': False, 'error': str(exc)}
    return {'success': True, 'summary': summary, 'citations': [], 'warnings': [DISCLAIMER]}


def compare_documents_ai(user, case, doc_a, doc_b, diff_summary):
    """AI explanation of a machine diff between two document versions."""
    if not can_view_case(user, case):
        return {'success': False, 'error': 'Not authorized to this case'}
    prompt = build_compare_prompt(doc_a.file_name, doc_b.file_name, diff_summary)
    try:
        explanation = _call_provider(prompt)
    except AIProviderError as exc:
        if 'not configured' in str(exc).lower() or 'GEMINI_API_KEY' in str(exc):
            return _not_configured_response()
        return {'success': False, 'error': str(exc)}
    return {'success': True, 'explanation': explanation, 'warnings': [DISCLAIMER]}
