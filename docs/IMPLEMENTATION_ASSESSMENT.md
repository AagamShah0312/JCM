# Implementation Assessment — JCM Enterprise v2

> Per spec §88 (FIRST ACTION): inspect the repository, then produce a concise
> implementation assessment before writing substantial code. This document is
> the assessment. It is written BEFORE the implementation begins and will be
> kept up to date as work proceeds.

## 1. Current architecture

Two projects live in one git repo (`Judicial-Cases-Management`):

1. **`JudicialCaseManagementSystem/`** — the main application.
   - **Backend**: Django 4.2 + Django REST Framework, JWT auth (simplejwt),
     SQLite-by-default (PostgreSQL optional via env), 6 apps:
     `authentication`, `cases`, `documents`, `notifications`,
     `ai_assistant`, `audit`.
   - **Frontend**: React 18 (CRA), Tailwind, Zustand, antd + custom CSS.
   - **Docker**: compose with postgres, redis, backend (gunicorn), celery,
     frontend, nginx.
2. `freellmapi/` — **removed** on `feat/gemini-migration` (Gemini migration completed).

The backend already has: custom `User` (email login, roles admin/judge/lawyer/guest,
`professional_id`), `Case` + `CaseTimeline` + `CaseAssignment` + `CaseNote`,
`CaseDocument` + `DocumentVersion` + `DocumentExtraction`,
`Notification`, `AIConversation`/`AIMessage`/`AIQuery`/`DocumentEmbedding`,
`AuditLog`.

## 2. Existing technologies

| Layer | Current | Target (spec) |
|---|---|---|
| Backend | Django 4.2 + DRF 3.14 + simplejwt | Django + DRF + Celery + Redis ✅ |
| DB | SQLite default / PostgreSQL optional | PostgreSQL + pgvector (primary) |
| Files | Local `MEDIA_ROOT` | S3-compatible abstraction (local default) |
| Frontend | React 18 (CRA) + Tailwind + Zustand + antd | **Next.js + TS + Tailwind + shadcn/ui + TanStack Query + RHF + Zod + Recharts + Lucide** |
| AI | Gemini via `services/ai_service.py` (`ask_gemini`, google-genai SDK) | AI provider abstraction (Gemini first), embeddings, retrieval w/ citations |
| Background | (Celery config present but minimal) | Celery + Redis for document pipeline + notifications |

## 3. Existing functionality (reusable)

- **Auth**: registration, login (JWT), profile, change-password, role-based
  `UserViewSet` with CSV staff import, promote/demote, analytics, login history.
  - CSV staff import exists but **lacks the preview/confirm/report flow** (spec §12).
- **Cases**: CRUD with role filtering, timeline events, notes, assignments,
  bookmarks, statistics, `update_hearing` (auto timeline event), documents
  upload-on-hearing-update.
  - **Missing**: multi-party, hearings as first-class entities, proceedings,
    orders, status transition validation, cause list, calendar, case health,
    what-changed, adjournment analytics, smart scheduling suggestions.
- **Documents**: upload (single/multi), extraction (pdfplumber/docx/txt/OCR),
  versioning model, download/extraction endpoints.
  - **Missing**: processing-state machine, async Celery pipeline, PyMuPDF,
    page-level extraction, chunking, embeddings (pgvector), visibility model
    (PUBLIC/LAWYER_ONLY/JUDGE_ONLY/RESTRICTED/ADMIN_ONLY), document access,
    signed/authorized download URLs, comparison of versions.
- **Notifications**: model + in-app CRUD, unread, mark read/all.
  - **Missing**: event-driven creation, Celery async delivery abstraction.
- **AI assistant**: case-aware chat + explain + summarize + timeline,
  conversation/message/query models, doc-text RAG over extraction.
  - **Missing**: citations (AICitation), permission-filtered retrieval,
    provider abstraction, chunk/vector store, hearing/document summaries,
    "authorization before retrieval" enforcement.
- **Audit**: basic `AuditLog` (create/update/delete/login/logout/download/upload).
  - **Missing**: event taxonomy (HEARING_RESCHEDULED, ORDER_PUBLISHED,
    DOCUMENT_VIEWED, PERMISSION_CHANGED, AI_QUERY…), append-only guarantee,
    middleware integration on sensitive operations.

## 4. What can be reused

- `User` model + authentication flow (extend with judge/lawyer profiles).
- `Case` model core (extend: CNR, priority, disposal, courts, transitions).
- `CaseDocument`/`DocumentVersion`/`DocumentExtraction` (extend: visibility,
  processing state, checksum, storage key, MIME).
- `Notification` model (extend event types).
- `AIConversation`/`AIMessage` (extend with citations).
- `AuditLog` model (extend event taxonomy + append-only).
- Django project layout, DRF wiring, JWT config, Docker skeleton.
- Gemini `ask_gemini()` as the seed of `GeminiProvider`.

## 5. What must be changed

- **Frontend**: full rewrite in Next.js + TypeScript (new app; CRA app kept
  until parity, per §84).
- **Backend structure**: add apps `courts`, `hearings`, `orders`, `tasks`,
  `analytics`; restructure `documents` and `ai` into pipelines/services.
- **Database**: switch primary dev DB to PostgreSQL + pgvector; new migration
  baseline.
- **Auth/permissions**: object/resource-level authorization service
  (not just `role == LAWYER`), role-specific serializers.
- **API surface**: move to `/api/v1/...` conventions, consistent error
  structure, server-side pagination everywhere.
- **Deletion**: soft-delete/archive semantics for judicial records.

## 6. Database changes required

- New models: Court, Courtroom, JudgeProfile, LawyerProfile, CaseParty,
  CaseLawyer, Hearing, HearingParticipant, HearingProceeding, Order,
  OrderVersion, DocumentAccess, DocumentChunk, CaseEvent, Task,
  AICitation, (pgvector) DocumentEmbedding v2, CaseStatusHistory.
- Extend: Case (CNR, priority, court, courtroom, disposal fields, status
  history), CaseDocument (visibility, processing state, checksum, storage key,
  MIME), Notification (event types), AuditLog (event taxonomy, request-id).
- pgvector extension + `vector` columns for embeddings; pg_trgm for fuzzy search.
- Indexes: case_number, cnr_number, status, court, judge, filing_date,
  next_hearing_date, case_type, document(case,hearing), hearing(date),
  order(date), audit(timestamp).

## 7. Backend changes required

- Settings: PostgreSQL+pgvector, Celery+Redis (broker/beat), S3 abstraction,
  AI provider config (chat/embedding models, temperature), rate limiting,
  security headers, request IDs, Sentry hook.
- New apps + serializers + viewsets for every entity with role-specific
  serializers; permission service; audit middleware; centralized error
  handler; CSV import (staff + cases) with preview/confirm/report;
  analytics endpoints; cause list; calendar; case health; what-changed;
  document comparison; hearing scheduling suggestions; notifications service
  (Celery); tasks.
- **Document pipeline** (Celery): upload → validate → store → process →
  extract (PyMuPDF) → OCR (Tesseract) → normalize → chunk → embed → index.
- **AI core**: provider abstraction (GeminiProvider first), embeddings
  service, retrieval service with authorization filtering, citation service,
  prompt library, structured AI response shape, safety constraints.

## 8. Frontend changes required

- Next.js + TS app: app shell (sidebar, top nav, breadcrumbs, search,
  notifications, profile), role-aware routing, dashboard for each role,
  case workspace (header + Overview/Timeline/Hearings/Proceedings/Documents/
  Orders/Parties/Tasks/AI/History tabs), cause list, calendar, case health,
  what-changed, document comparison UI, admin CSV import wizard, guest public
  search, forms (RHF+Zod), tables (sort/filter/paginate/column visibility),
  AI panel with clickable citations, empty/loading/error states.

## 9. AI/document-processing changes required

- Document: PyMuPDF text extraction + page rendering for OCR; OpenCV
  preprocessing; Tesseract; page-level metadata; chunking; embeddings
  (pgvector); processing-state machine; Celery orchestration.
- AI: provider abstraction, retrieval that filters by case/document/visibility
  authorization BEFORE vector search, citation generation, prompt templates
  enforcing no-fabrication and no-judicial-decision rules, hearing/document
  summarizers, structured answer+citations response.

## 10. Security/authorization gaps

- No object-level permission service (role-only checks today).
- Document visibility not modeled; raw media URLs exposed (need signed URLs).
- No CSV preview/validation-gate (imports insert directly today).
- Audit is minimal and not append-only enforced.
- Guest API currently reuses authenticated serializers (must be restricted).
- No rate limiting on sensitive endpoints beyond DRF defaults; no file MIME
  sniffing/checksum; no request-ID logging.

## Priority order (per spec §88 last line)

**correctness → security → data integrity → maintainability → functionality → visual polish.**

## Implementation phases

1. **P1 Backend backbone**: apps + full data model + migrations (PostgreSQL+pgvector) + permission service + settings. ✅ *in progress*
2. **P2 Document pipeline + AI core**: Celery tasks, storage, embeddings, provider abstraction, permission-filtered retrieval, citations.
3. **P3 API layer**: serializers/views per role, error handling, CSV import wizard, analytics, cause list, calendar, case health, what-changed, comparison, notifications.
4. **P4 Frontend**: Next.js app shell + dashboards + case workspace + guest portal + admin console.
5. **P5 Infra/quality**: docker-compose, tests, seed data, docs, end-to-end demo.
