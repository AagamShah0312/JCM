# Judicial Case Management System (JCM)

A production-grade, role-based judicial case management platform for India —
cases, parties, judges, lawyers, hearings, proceedings, orders, documents,
timelines, permissions, notifications, audit trails, search, analytics, and
AI-assisted case intelligence.

> **Stack:** Django 4.2 + DRF + Celery + Redis · PostgreSQL + pgvector ·
> Next.js 14 + TypeScript + Tailwind · Google Gemini (AI)

## Roles

| Role | Experience |
|---|---|
| **Judge** | Dashboard (today's/upcoming hearings, cause list, pending/urgent), case workspace, hearings (create/reschedule/complete), proceedings, orders, documents, status transitions |
| **Lawyer** | Dashboard (my cases, what changed, notifications), case workspace tabs, tasks, Case AI with citations |
| **Admin** | System dashboard, cases/users/courts/courtrooms management, CSV import wizard (validate → preview → confirm → report), analytics |
| **Guest / Public** | Public case search + public timeline/hearings/orders/documents (anonymous) — never restricted content |

## Key features

- **Enterprise data model** — multi-party cases, first-class hearings with
  proceedings/participants, orders separate from documents with versioning,
  configurable statuses/priorities/adjournment reasons.
- **Document pipeline (async)** — upload → PyMuPDF extraction → OCR
  (Tesseract) for scanned PDFs → page-aware chunking → pgvector embeddings.
  Processing states tracked; failures never corrupt originals.
- **Case AI assistant** — case-aware Q&A, case/hearing/document summaries,
  **authorization before retrieval**, clickable citations, safety-constrained
  prompts, provider abstraction (Gemini default).
- **Strict document visibility** — PUBLIC / LAWYER_ONLY / JUDGE_ONLY /
  RESTRICTED / ADMIN_ONLY + explicit grants; signed download URLs.
- **Audit trail** — append-only logging of all sensitive operations
  (login, case/hearing/order/doc events, reschedules, downloads, AI queries).
- **Admin analytics** — case stats, by type/court/judge, age distribution,
  adjournment analytics, attention flags; cause list; calendar; case health;
  smart hearing scheduling suggestions.
- **CSV import wizard** — staff (judges/lawyers) and cases with
  parse → validate → preview → confirm → import → report; no unvalidated inserts.
- **Guest portal** — public search and public case pages, restricted
  serializers only.
- **Consistent error format** — `{"success": false, "error": {code, message}}`.

## Quick start (local)

```bash
cd JudicialCaseManagementSystem
cp .env.example .env          # set GEMINI_API_KEY (free: aistudio.google.com/apikey)

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo    # optional rich fictional demo data
python manage.py runserver    # http://localhost:8000

# Frontend (Next.js)
cd ../frontend-next
npm install
npm run dev                   # http://localhost:3000
```

Docker: `docker compose -f docker/docker-compose.yml up --build`

## Demo accounts (seed data)

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | Aagam%1234 |
| Judge | judge.mehta@example.com | Aagam%1234 |
| Lawyer | lawyer.shah@example.com | Aagam%1234 |

## Testing

```bash
cd backend
python manage.py test         # 24 tests incl. permission & security tests
```

## Documentation

- `docs/ARCHITECTURE.md` — system architecture
- `docs/API.md` — REST API reference
- `docs/DATABASE.md` — schema
- `docs/AI.md` — AI system, providers, citations, safety
- `docs/SECURITY.md` — security model
- `docs/DEPLOYMENT.md` — setup, Docker, production
- `docs/IMPLEMENTATION_ASSESSMENT.md` — pre-implementation assessment

## Notes

- All seed/demo data is fictional.
- AI output is advisory only; it never decides cases.
- The legacy React (CRA) frontend remains in `frontend/` until the Next.js app
  reaches full parity (see `frontend-next/`).
