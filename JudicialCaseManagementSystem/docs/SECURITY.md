# JCM Security

Security is treated as a core feature (spec §46).

## Authentication

- JWT access tokens (15 min) + refresh tokens (1 day) with rotation and
  blacklisting (simplejwt `token_blacklist`).
- Passwords hashed (Django PBKDF2/bcrypt); strength validated
  (uppercase, digit, special char).
- **MFA-ready architecture**: `TwoFactorAuth` model (per-user enable flag,
  provider: TOTP/WebAuthn/SMS/Email, encrypted secret slot) + `MFA_ENABLED`
  setting + `GET /api/auth/mfa/status/` endpoint. A concrete TOTP/WebAuthn
  provider is intentionally not bundled — set `MFA_ENABLED=True` and add a
  provider (e.g. django-otp/pyotp) to enable enrollment. The login flow can
  then require a challenge after password verification.

## Authorization

- **Backend is the final authority.** Frontend route guards are UX only.
- Object/resource-level checks in `apps/cases/permissions.py`
  (never just `role == LAWYER`).
- Role-specific serializers: guest API never reuses full authenticated
  serializers; restricted fields are simply absent.
- Document visibility: PUBLIC / LAWYER_ONLY / JUDGE_ONLY / RESTRICTED /
  ADMIN_ONLY + explicit per-user grants (`DocumentAccess`).
- AI retrieval: authorization BEFORE retrieval (§34); the model can never
  see unauthorized chunks.

## API security

- Centralized error handler never leaks stack traces (`INTERNAL_ERROR`).
- Rate limiting via DRF throttles (anon 100/hr, user 1000/hr; adjust in
  settings).
- CORS restricted to configured origins (never `*` in production).
- Request-ID header (`X-Request-ID`) on every response for traceability.
- CSRF: API is token-auth (CSRF not required); admin site keeps CSRF.

## File uploads

- Extension whitelist (pdf, docx, doc, jpg, jpeg, png, txt).
- Size limit 20 MB.
- MIME type captured; SHA-256 checksum stored.
- Files stored via storage abstraction (local dev / S3 in prod); sensitive
  documents use **signed/authorized download URLs** — raw permanent S3 URLs
  are never exposed to clients. Download attempts are audited.

## Secrets

- All keys come from environment variables (`.env`, gitignored).
- `.env.example` documents required vars with empty placeholders.
- Never hard-code API keys; never ship `.env`.

## Audit

- Append-only `AuditLog` (`delete()` raises `NotImplementedError`).
- Sensitive actions logged: LOGIN/LOGOUT, CASE_*, HEARING_* (incl.
  RESCHEDULED), PROCEEDINGS_*, DOCUMENT_* (incl. VIEWED/DOWNLOADED),
  ORDER_*, USER_*, PERMISSION_CHANGED, CSV_IMPORT, AI_QUERY.
- Audit middleware + explicit `record_audit` calls.

## Data protection

- Sensitive personal information is only exposed where explicitly marked
  public (parties have `is_public`).
- Guest API intentionally restricted.
- Soft deletion / archival for judicial records; no casual cascades.

## Deployment hardening (production)

- HTTPS + `SECURE_SSL_REDIRECT`, secure cookies, XSS filter, CSP header
  (enabled automatically when `DEBUG=False`).
- `ALLOWED_HOSTS` set explicitly.
- Database credentials via env; PostgreSQL user least-privilege.
- Sentry SDK wired for error tracking (set `SENTRY_DSN`).
