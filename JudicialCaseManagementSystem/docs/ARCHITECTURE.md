# JCM Architecture

## Overview

JCM (Judicial Case Management) is a production-grade case-management platform
for Indian courts. It is built as two projects in one repository:

```
JudicialCaseManagementSystem/
├── backend/          # Django 4.2 + DRF + Celery + PostgreSQL/pgvector
├── frontend-next/    # Next.js 14 + TypeScript + Tailwind + TanStack Query
├── frontend/         # Legacy React (CRA) app — kept until Next.js reaches parity
├── docker/           # docker-compose (backend, frontend-next, postgres, redis, worker)
└── docs/
```

## Backend (Django)

Apps:

| App | Responsibility |
|---|---|
| `authentication` | User model (roles: admin/judge/lawyer/guest), JWT auth, profiles, CSV import wizard |
| `courts` | Court + Courtroom |
| `cases` | Case hub: Case, CaseParty (multi-party), CaseLawyer, CaseEvent (timeline), status history, permission service |
| `hearings` | First-class Hearing, HearingParticipant, HearingProceeding, adjournment reasons |
| `orders` | Order (DRAFT/SIGNED/PUBLISHED/SUPERSEDED) + version history |
| `documents` | Document metadata, visibility, processing states, chunks, embeddings (pgvector), pipeline |
| `tasks` | Judge/lawyer work items |
| `notifications` | Event-driven in-app notifications (Celery async) |
| `ai_assistant` | Conversations, messages, citations |
| `ai` | AI provider abstraction, embeddings, permission-filtered retrieval, prompts, services |
| `audit` | Append-only audit log |
| `analytics` | Admin stats, cause list, calendar, case health, what-changed, scheduling suggestions |
| `common` | Centralized error handler, request-ID + audit middleware |

### Authorization model

Object/resource-level authorization lives in `apps/cases/permissions.py`:

- `can_view_case` / `can_edit_case` / `case_queryset_for`
- `can_view_document` / `can_download_document` / `document_queryset_for`
- `can_view_hearing` / `can_edit_hearing` / `can_view_order` / `can_view_proceeding` / `can_view_task`

Role-specific serializers (§69): `GuestCaseSerializer`, `LawyerCaseSerializer`,
`JudgeCaseSerializer`, `AdminCaseSerializer`; guest document/hearing/order
serializers are intentionally restricted.

### Document pipeline

```
Upload → validate → store original → Celery task:
  PyMuPDF text extraction → scanned? → OpenCV preprocess → Tesseract OCR
  → normalize → chunk (page-aware) → store chunks → pgvector embeddings
States: UPLOADED → PROCESSING → PROCESSED | OCR_COMPLETED | FAILED
```

### AI architecture

```
User question → can_view_case? → authorize documents (visibility + grants)
→ vector retrieval over authorized chunks only → LLM (Gemini default)
→ answer + citations (AICitation) + warnings
```

Provider abstraction (`apps/ai/providers.py`): `GeminiProvider` (default),
`OpenAIProvider`, `AnthropicProvider`, `LocalProvider` — selected via
`AI_PROVIDER` env var. Keys come from environment variables only.

## Frontend (Next.js)

- App Router (`app/`), server-side rewrites proxy `/api/*` → Django.
- TanStack Query for data fetching, Zustand for auth, RHF+Zod forms,
  Recharts for analytics, Lucide icons.
- Role-aware routing: `/admin/*`, `/judge/*`, `/lawyer/*`, `/guest/*`,
  `/cases/*`, `/cause-list`, `/tasks`, `/notifications`.
- Case workspace tabs: Overview, Timeline, Hearings, Proceedings, Documents,
  Orders, Parties, Tasks, AI Assistant (with clickable citations).
- Public guest portal at `/guest/*` (anonymous) — public search + case view.

## Docker

`docker-compose.yml` runs: postgres (with pgvector), redis, backend
(gunicorn), celery worker, frontend-next, nginx. See DEPLOYMENT.md.
