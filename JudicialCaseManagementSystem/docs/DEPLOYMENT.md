# JCM Deployment

## Local development (recommended)

```bash
# 1. Backend
cd JudicialCaseManagementSystem
cp .env.example .env          # set GEMINI_API_KEY etc.
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo    # optional rich fictional data
python manage.py runserver    # http://localhost:8000

# 2. Frontend (Next.js)
cd ../frontend-next
npm install
npm run dev                   # http://localhost:3000 (proxies /api to :8000)

# 3. (Optional) Celery worker for async document processing
cd ../backend
celery -A judicial_backend worker -l info
```

> In dev, Celery tasks run eagerly (`CELERY_TASK_ALWAYS_EAGER=True`) so the
> document pipeline works without a worker. Set it to `False` in production.

## Docker (docker compose)

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

Services: `postgres` (pgvector), `redis`, `backend` (gunicorn),
`celery_worker`, `frontend-next`, `nginx` (port 80).

## Environment variables

See `.env.example`. Key ones:

| Var | Purpose |
|---|---|
| `DB_ENGINE` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL |
| `GEMINI_API_KEY` | Google AI Studio key (blank disables AI gracefully) |
| `GEMINI_MODEL` | e.g. `gemini-2.5-flash` |
| `AI_PROVIDER` | `gemini` (default) / `openai` / `anthropic` / `local` |
| `STORAGE_BACKEND` | `local` (default) / `s3` |
| `S3_ENDPOINT` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_REGION` | S3-compatible storage |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis URLs |
| `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` | Hosts/origins |
| `SECRET_KEY` | Django secret |

## Production notes

- Set `DEBUG=False` (enables SSL redirect, secure cookies, CSP).
- Run with gunicorn: `gunicorn judicial_backend.wsgi:application --bind 0.0.0.0:8000`.
- Run a real Celery worker + beat for async processing/notifications.
- Use S3-compatible object storage for documents.
- Back up PostgreSQL (`pg_dump`) and media/object storage regularly.
- Sentry: set `SENTRY_DSN` for error tracking.

## Testing

```bash
cd backend
python manage.py test          # 24 tests: models, API, permissions, security, AI
```

## Demo flow

1. Admin creates judge/lawyer/case, assigns both.
2. Judge opens case → schedules hearing → records proceedings → uploads order → publishes.
3. Document pipeline processes + indexes.
4. Lawyer opens case → sees order → asks Case AI "What happened in the latest
   hearing?" → answer with citations.
5. Guest searches public case → sees public timeline/hearings; cannot access
   restricted documents.
