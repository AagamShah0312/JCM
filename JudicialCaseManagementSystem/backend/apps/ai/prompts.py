"""
Prompt templates for the Case AI (spec §74).

Every prompt instructs the model to:
- use only supplied sources
- avoid inventing facts / citations / authorities
- state when information is unavailable
- cite source documents
- distinguish source facts from inference
- never make judicial decisions, verdicts, or binding recommendations
"""

SYSTEM_SAFETY = (
    "You are the AI assistance layer inside a Judicial Case Management system. "
    "You help users understand case information. You must NEVER: decide guilt or "
    "innocence, determine a judicial outcome, issue or recommend a binding ruling, "
    "pretend to be a judge, invent legal authorities, invent case citations, or "
    "invent facts. All your output is ADVISORY and should be verified against "
    "source documents. If information is not available in the supplied context, "
    "say so clearly. Distinguish source facts from your own inference. "
    "Cite the supplied sources where relevant. Do not reveal internal reasoning; "
    "only provide concise, user-facing source explanations."
)


def build_qa_prompt(case, query, context, history=None):
    """
    Build a Q&A prompt for a case-aware assistant.
    context: dict from apps.ai.retrieval.retrieve_case_context
    """
    case_block = (
        f"Case Number: {case.case_number}\n"
        f"Title: {case.title}\n"
        f"Status: {case.get_status_display()}\n"
        f"Type: {case.case_type}\n"
        f"Filing Date: {case.filing_date.isoformat() if case.filing_date else 'N/A'}\n"
        f"Next Hearing: {case.next_hearing_date.isoformat() if case.next_hearing_date else 'N/A'}\n"
    )

    chunk_lines = []
    for i, item in enumerate(context.get('chunks', []), start=1):
        doc = item['document']
        page = f" (page {item['page_number']})" if item['page_number'] else ''
        chunk_lines.append(
            f"[Source {i}] {doc.file_name}{page}\n{item['text'][:1500]}"
        )
    chunk_block = '\n\n'.join(chunk_lines) if chunk_lines else 'No document sources matched.'

    hearings_block = '\n'.join(
        f"- Hearing #{h['number']} on {h.get('date')}: {h.get('status')} ({h.get('purpose') or 'no purpose'})"
        for h in context.get('hearings', [])
    ) or 'No hearings available.'

    proceedings_block = '\n'.join(
        f"- {p.get('summary', '')[:300]}"
        for p in context.get('proceedings', [])
    ) or 'No proceedings available.'

    orders_block = '\n'.join(
        f"- {o.get('title')} ({o.get('date')}) [{o.get('status')}]: {o.get('summary', '')[:300]}"
        for o in context.get('orders', [])
    ) or 'No orders available.'

    history_block = 'No prior conversation.'
    if history:
        lines = [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-8:]]
        history_block = '\n'.join(lines)

    return (
        f"{SYSTEM_SAFETY}\n\n"
        f"CASE DETAILS\n{case_block}\n"
        f"CONVERSATION HISTORY\n{history_block}\n\n"
        f"RELEVANT DOCUMENTS (authorized for this user)\n{chunk_block}\n\n"
        f"HEARINGS\n{hearings_block}\n\n"
        f"PROCEEDINGS\n{proceedings_block}\n\n"
        f"ORDERS\n{orders_block}\n\n"
        f"USER QUESTION\n{query}\n\n"
        "Answer using only the supplied context. Where you rely on a source, "
        "mention it by name (e.g. 'per Hearing #3 proceedings' or 'per "
        "document.pdf p.2'). If the context does not contain the answer, say "
        "the information is not available in the case file. Do not invent "
        "anything. Keep the answer clear and concise.\n"
    )


def build_summary_prompt(case, context, summary_type='case'):
    if summary_type == 'case':
        instruction = (
            "Summarize this case in a concise overview: case type, parties, "
            "filing date, current status, major events, major hearings, "
            "important orders, current next hearing, and key documents. "
            "Use short sections. Only use supplied information."
        )
    elif summary_type == 'hearing':
        instruction = (
            "Summarize the hearings of this case: what happened at each "
            "hearing (date, status, purpose, adjournment reason if any, "
            "proceedings summary). Keep it factual and concise."
        )
    elif summary_type == 'document':
        instruction = (
            "Summarize the authorized documents of this case. For each "
            "document, give its name, type, and a 1-2 sentence factual "
            "summary of its content. Only summarize documents shown."
        )
    else:
        instruction = "Summarize this case concisely using only the supplied information."

    return build_qa_prompt(case, instruction, context, history=None)


def build_change_summary_prompt(case, changes):
    """Prompt to produce a human-friendly 'What changed?' summary."""
    changes_block = '\n'.join(f"- {c}" for c in changes) or 'No changes detected.'
    return (
        f"{SYSTEM_SAFETY}\n\n"
        f"Case: {case.case_number} — {case.title}\n"
        f"CHANGES SINCE LAST VISIT\n{changes_block}\n\n"
        "Write a short, friendly summary of what changed in this case. "
        "Group similar items. Do not add facts that are not in the list."
    )


def build_compare_prompt(doc_a_name, doc_b_name, diff_summary):
    return (
        f"{SYSTEM_SAFETY}\n\n"
        f"You are comparing two versions of a document: '{doc_a_name}' (older) "
        f"and '{doc_b_name}' (newer).\n"
        f"MACHINE DIFF SUMMARY:\n{diff_summary}\n\n"
        "Explain the differences in plain language: what was added, what was "
        "removed, and what was modified. Label this as AI-generated comparison "
        "and remind the user to verify against the actual documents."
    )
