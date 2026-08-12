# JCM — What You Need To Do (from scratch)

This is the step-by-step checklist to run the Judicial Case Management System
on your machine. Everything is committed on branch `feat/jcm-enterprise-v2`
(merge into `main` when ready). Follow the order below.

---

## 0. Prerequisites to install (once)

| Tool | Version | Why |
|---|---|---|
| Python | 3.11–3.12 recommended | Backend (Django). 3.13 works too. |
| Node.js | 20+ | Next.js frontend |
| PostgreSQL | 15+ | Database (required — not SQLite) |
| Redis | 7 | Celery broker + cache (optional for dev) |
| Tesseract OCR | latest | Scanned-document OCR pipeline |
| Docker (optional) | — | One-command alternative to steps 1–6 |

---

## 1. Get the code

```bash
git clone https://github.com/AagamShah0312/Judicial-Cases-Management.git
cd Judicial-Cases-Management
git checkout feat/jcm-enterprise-v2   # this branch has the full enterprise build
```

---

## 2. Backend environment — the `.env` file (most important step)

```bash
cd JudicialCaseManagementSystem
cp .env.example .env
```

Open `.env` and **fill in these values**:

```env
DEBUG=True
SECRET_KEY=generate-a-long-random-string     # python -c "import secrets; print(secrets.token_urlsafe(50))"
ALLOWED_HOSTS=localhost,127.0.0.1

# Database — match your local PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=judicial_case_db
DB_USER=postgres
DB_PASSWORD=your-postgres-password          # <-- enter your postgres password here
DB_HOST=localhost
DB_PORT=5432

# AI — get a free key at https://aistudio.google.com/apikey
GEMINI_API_KEY=                              # <-- paste your Gemini key here to turn AI ON
GEMINI_MODEL=gemini-2.5-flash

# Optional: MFA
MFA_ENABLED=False                            # set True to enable two-factor auth

# Optional: email notifications (leave as-is to skip)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Then create the database:

```bash
# start PostgreSQL, then:
psql -U postgres -c "CREATE DATABASE judicial_case_db;"
psql -U postgres -d judicial_case_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d judicial_case_db -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

---

## 3. Install backend + migrate + seed

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate           # creates all tables (incl. pgvector)
python manage.py seed_demo         # optional rich fictional demo data
python manage.py runserver         # http://localhost:8000
```

> `seed_demo` creates demo users: admin@example.com, judge.mehta@example.com,
> lawyer.shah@example.com, guest.public@example.com — password `Aagam%1234`.

---

## 4. Frontend (Next.js)

```bash
cd ../frontend-next
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev                        # http://localhost:3000
```

The app proxies `/api` → Django automatically. Login with a demo account.

---

## 5. (Optional) Celery worker + beat — async document processing & notifications

Open a third terminal:

```bash
cd backend
source .venv/bin/activate
celery -A judicial_backend worker -l info
celery -A judicial_backend beat -l info     # separate terminal
```

> In development you can skip this: tasks run eagerly
> (`CELERY_TASK_ALWAYS_EAGER=True` is the default in `.env`).

---

## 6. (Optional) Docker instead of steps 3–5

```bash
cp .env.example .env   # fill DB + GEMINI_API_KEY
docker compose -f docker/docker-compose.yml up --build
```

Starts: postgres (pgvector), redis, backend, celery worker, frontend, nginx
on port 80.

---

## 7. Tests (verify everything works)

```bash
cd backend && source .venv/bin/activate
python manage.py test                     # 46 backend tests
cd ../frontend-next
npm test                                  # 13 frontend component tests
```

---

## 8. Things that need YOUR credentials/actions (not code)

| Item | Where | What to enter |
|---|---|---|
| **Gemini API key** | `.env` → `GEMINI_API_KEY=` | Paste key from aistudio.google.com/apikey — **this is the one thing that turns the AI on** |
| **Postgres password** | `.env` → `DB_PASSWORD=` | Your local postgres password |
| **SECRET_KEY** | `.env` → `SECRET_KEY=` | Random string (see §2) |
| **MFA enrollment** | Settings page (per user) | After setting `MFA_ENABLED=True`, log in → Settings → scan QR with Google Authenticator → **save the 10 recovery codes** it shows (Settings → "Recovery codes") |
| **Email/SMS/push** | `.env` → `EMAIL_*`, or future SMS/push providers | Optional; in-app notifications work without it |
| **CI workflow** | `.github/workflows/ci.yml` (already committed) | Runs automatically on GitHub — Django tests on a pgvector service + Next.js build |
| **S3 storage** | `.env` → `STORAGE_BACKEND=s3` + `S3_*` | Only if you want S3 instead of local file storage |

---

## 9. Recovery codes & WebAuthn (if you enable MFA)

- When you enable 2FA (Settings → scan QR → verify), the app shows **10 one-time
  recovery codes** — save them. If you lose your authenticator app, enter a
  recovery code at login instead of the 6-digit TOTP code.
- Settings → **Recovery codes** lists them (masked); **Regenerate** issues 10
  new ones and invalidates the old.
- **WebAuthn / passkeys** appear in Settings as a status ("provider not wired").
  To actually use passkeys you'd add a WebAuthn server (e.g. `py_webauthn`) +
  browser `navigator.credentials` integration — the data model and endpoint
  are ready.

## 10. Demo walkthrough (spec §63) to confirm everything is wired

1. Log in as **admin** → create a court (Courts page) → create a case (Cases → New Case)
2. Log in as **judge** → open the case → Hearings tab → Schedule a hearing →
   try "Suggest dates" → Complete + record proceedings → Orders tab → Create +
   Publish an order → Documents tab → upload a file (watch it go PROCESSED)
3. Log in as **lawyer** → open the case → see the order → AI Assistant tab →
   ask "What happened in the latest hearing?" (works once GEMINI_API_KEY is set)
4. Guest/anonymous → public search → open the public case → timeline/hearings;
   try to open a JUDGE_ONLY document → 404

---

## Notes

- **Legacy frontend**: the old React (CRA) app remains in `frontend/` but the
  active frontend is `frontend-next/`. The CRA app can be deleted once you've
  validated the Next.js app.
- **All endpoints** are listed in `docs/API.md`.
- **Architecture / security / deployment** details: `docs/ARCHITECTURE.md`,
  `docs/SECURITY.md`, `docs/DEPLOYMENT.md`.
- **AI is advisory**: it never decides cases; answers carry a disclaimer.
