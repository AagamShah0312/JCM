# JCM — Judicial Case Management

Production-grade, role-based judicial case management platform for India.

The product is the **case lifecycle**: cases, parties, judges, lawyers, hearings, proceedings, documents, orders, timelines, permissions, notifications, audit trails, search, analytics, and AI-assisted case intelligence.

AI assists users. It never makes judicial decisions.

## Roles

| Role | Experience |
|---|---|
| **Judge** | Today's cause list, hearings, proceedings, orders, authorized cases |
| **Lawyer** | Assigned cases, what changed, documents/orders they may see, case AI |
| **Admin** | Users, courts, CSV import (preview → confirm), analytics, audit |
| **Guest** | Public case search only — no restricted documents or internal notes |

## Stack

| Layer | Technology |
|---|---|
| Frontend | **Next.js 15**, React 19, TypeScript, Tailwind CSS, TanStack Query, React Hook Form, Zod, Recharts, Lucide |
| Backend | **Django 5.2 LTS**, Django REST Framework, Celery, Redis |
| Database | **PostgreSQL 16 + pgvector** |
| Files | S3-compatible abstraction (local filesystem or MinIO/AWS) |
| AI | Provider abstraction (Gemini default, OpenAI / Anthropic / local stubs) |
| Runtime | **Node 22 LTS**, **Python 3.12**, Docker Compose |

The legacy Create-React-App app under `frontend/` is kept for reference only. **`frontend-next/` is the application.**

## Quick start (Docker)

```bash
cp .env.example .env          # add GEMINI_API_KEY if you want live AI
docker compose up --build
```

- App: http://localhost:3000
- API: http://localhost:8000/api/
- Health: http://localhost:8000/health/
- MinIO console: http://localhost:9001

Demo accounts (seeded automatically, all fictional):

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | `Aagam%1234` |
| Judge | judge.mehta@example.com | `Aagam%1234` |
| Lawyer | lawyer.shah@example.com | `Aagam%1234` |
| Guest | guest.public@example.com | `Aagam%1234` |

## Local development (without Docker)

**Prerequisites:** Python 3.12+, Node.js 22+, PostgreSQL 16 with pgvector, Redis 7.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000

# Frontend (second terminal)
cd frontend-next
npm install
npm run dev
```

Optional Celery worker (document OCR / embeddings / notifications):

```bash
cd backend
celery -A judicial_backend worker -l info
```

With `CELERY_TASK_ALWAYS_EAGER=True` (default in `.env.example`) tasks run in-process.

## Project layout

```
jcm/
├── frontend-next/     Next.js 15 app (pages, components, lib, hooks, types)
├── frontend/          Legacy CRA (not used)
├── backend/
│   ├── judicial_backend/   Django settings, URLs, Celery
│   ├── apps/               users, courts, cases, hearings, orders,
│   │                       documents, notifications, tasks, audit,
│   │                       analytics, ai / ai_assistant
│   └── services/           storage + AI provider wrappers
├── docker/            Dockerfiles + nginx
├── docs/              ARCHITECTURE, API, DATABASE, AI, SECURITY, DEPLOYMENT
├── docker-compose.yml
└── .env.example
```

## API

REST under `/api/` and `/api/v1/`. Consistent error envelope:

```json
{ "success": false, "error": { "code": "CASE_NOT_FOUND", "message": "…" } }
```

Highlights:

- `POST /api/auth/login/` · `GET /api/auth/profile/` · MFA under `/api/auth/mfa/`
- `GET/POST /api/cases/` · hearings, documents, orders, timeline, parties
- `GET /api/public/cases/` — guest serializers only (no private fields)
- `GET /api/search/` — global search
- `POST /api/ai/cases/{id}/chat/` — case-scoped RAG with citations
- `GET /api/analytics/admin/` · cause-list · calendar · case health · what-changed

See [docs/API.md](docs/API.md).

## Documents & AI

Upload → validate → store original → Celery process (PyMuPDF → OCR if needed → chunk → embed in pgvector). Retrieval **filters by case + document visibility before** calling the LLM. Answers include citations. The model is instructed not to invent facts or issue rulings.

## Tests

```bash
cd backend && python manage.py test
cd frontend-next && npm test
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Database](docs/DATABASE.md)
- [AI](docs/AI.md)
- [Security](docs/SECURITY.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Implementation assessment](docs/IMPLEMENTATION_ASSESSMENT.md)

## Legal note

This is software for case *management*. Security features do not make the system legally compliant with any specific Indian judicial regulation. Jurisdiction-specific rules should stay configurable. AI output is advisory and must be verified against source documents.

## License

MIT
