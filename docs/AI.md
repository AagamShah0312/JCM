# JCM AI System

## Overview

The Case AI Assistant is case-aware and permission-filtered. It never answers
from content the user cannot access, and it never makes judicial decisions.

```
User question
  → can_view_case(user, case)?
  → authorize documents (visibility + explicit grants)
  → vector retrieval over AUTHORIZED chunks only (pgvector)
  → LLM (Gemini by default) with safety-constrained prompt
  → { answer, citations, sources, warnings }
```

## Providers

`AI_PROVIDER` env var selects the provider (default `gemini`):

| Provider | Env vars |
|---|---|
| `gemini` (default) | `GEMINI_API_KEY`, `AI_CHAT_MODEL` (default gemini-2.5-flash), `AI_EMBEDDING_MODEL` (default gemini-embedding-001) |
| `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `local` | `OLLAMA_BASE_URL` |

`AI_TEMPERATURE`, `AI_MAX_OUTPUT_TOKENS`, `AI_PROVIDER` are configurable.

## Permission filtering (critical)

`apps/ai/retrieval.py` implements **authorization before retrieval**:

1. `can_view_case(user, case)` — if not allowed, return nothing.
2. `authorized_document_ids(user, case)` — iterate case documents and keep only
   those where `can_view_document(user, doc)` is true (visibility + grants).
3. Vector similarity runs only over chunks of those authorized documents.
4. Keyword fallback (pg_trgm/icontains) also runs only over authorized chunks.

The AI can never retrieve or cite content the user cannot access.

## Citations

Every factual answer should reference sources. `AICitation` stores:
source type (case/hearing/proceeding/document/order/chunk), source id, label,
page number, chunk index, excerpt, url. The frontend renders them as clickable
chips; deep links open the relevant tab.

## Safety constraints

Prompts (see `apps/ai/prompts.py`) instruct the model to:
- use only supplied sources; never invent facts, authorities or citations
- state when information is unavailable
- distinguish source facts from inference
- never decide guilt/innocence, issue rulings, or recommend binding outcomes
- never pretend to be a judge

All answers carry the warning: "AI-generated assistance — advisory only."

## Document pipeline → AI indexing

```
Upload → validate → store → extract (PyMuPDF) → OCR (Tesseract) if scanned
→ normalize → chunk (page-aware) → store chunks → pgvector embeddings → index
```

Chunk metadata: document_id, case_id, hearing_id, page_number, chunk_index,
text, embedding, visibility, document_version. Retrieval filters by
case authorization, document authorization, visibility, and document state.

## API

- `GET/POST /api/ai/cases/{case_id}/chat/`
- `GET /api/ai/cases/{case_id}/explain/` (cached)
- Summaries: case, hearing, documents (via `apps/ai/services.py`)
- What-changed AI summary, document comparison AI explanation

## Setup

```bash
cp .env.example .env   # set GEMINI_API_KEY
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
