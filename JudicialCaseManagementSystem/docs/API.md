# JCM API Reference

Base URL: `http://localhost:8000/api` (proxied by the Next.js app under `/api`).

Auth: `Authorization: Bearer <access_token>` (JWT). Obtain via
`POST /api/auth/login/`. Refresh via `POST /api/auth/token/refresh/`.

## Error format

All errors use a consistent envelope:

```json
{ "success": false, "error": { "code": "CASE_NOT_FOUND", "message": "…" } }
```

## Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register/` | Register (lawyer role) |
| POST | `/auth/login/` | Login → `{user, access, refresh}` |
| POST | `/auth/logout/` | Logout (blacklists refresh) |
| GET/PUT | `/auth/profile/` | Get/update own profile |
| POST | `/auth/change-password/` | Change password |
| GET | `/auth/users/` | List users (role-scoped) |
| POST | `/auth/csv/staff/preview/` | Preview staff CSV (parse+validate+dup-check) |
| POST | `/auth/csv/staff/import/` | Confirm + import staff rows |
| POST | `/auth/csv/cases/preview/` | Preview cases CSV |
| POST | `/auth/csv/cases/import/` | Confirm + import case rows |

## Cases

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/cases/` | List (role-scoped, filterable) |
| POST | `/cases/` | Create (admin/judge) |
| GET/PATCH | `/cases/{id}/` | Retrieve/update (authorized) |
| DELETE | `/cases/{id}/` | Soft-delete (archive) — admin only |
| GET | `/cases/{id}/timeline/` | Timeline events |
| POST | `/cases/{id}/change_status/` | Validated status transition |
| GET/POST | `/cases/{id}/parties/` | Multi-party management |
| POST | `/cases/{id}/assign_lawyer/` | Assign lawyer (idempotent) |
| GET | `/cases/upcoming_hearings/` | Upcoming hearings |

## Hearings

| Method | Endpoint | Notes |
|---|---|---|
| GET/POST | `/hearings/` | List/create |
| GET/PATCH | `/hearings/{id}/` | Detail/update |
| POST | `/hearings/{id}/reschedule/` | Reschedule (audited) |
| POST | `/hearings/{id}/complete/` | Complete + record proceedings |
| POST | `/hearings/{id}/cancel/` | Cancel |
| GET/POST | `/hearings/{id}/participants/` | Attendance |
| GET/POST | `/hearings/{id}/proceedings/` | Proceedings |
| GET | `/hearings/adjournment-reasons/` | Configurable reasons |

## Orders

| Method | Endpoint | Notes |
|---|---|---|
| GET/POST | `/orders/` | List/create (draft by default) |
| GET/PATCH | `/orders/{id}/` | Detail/update |
| POST | `/orders/{id}/publish/` | Publish (notifies parties) |
| POST | `/orders/{id}/sign/` | Mark signed |
| POST | `/orders/{id}/supersede/` | Mark superseded |
| POST | `/orders/{id}/new_version/` | Append-only version |

## Documents

| Method | Endpoint | Notes |
|---|---|---|
| GET/POST | `/documents/` | List/upload (multi-file; triggers async pipeline) |
| GET | `/documents/{id}/` | Detail (visibility-checked) |
| GET | `/documents/{id}/download/` | Authorized signed download URL |
| GET | `/documents/{id}/extraction/` | Extracted text + page metadata |
| GET | `/documents/{id}/chunks/` | Searchable chunks |
| POST | `/documents/{id}/new_version/` | New version (no overwrite) |
| POST | `/documents/{id}/compare/` | Version comparison (+ AI summary) |
| POST | `/documents/{id}/grant_access/` | Explicit per-user grant (admin) |
| POST | `/documents/{id}/set_visibility/` | Change visibility (audited) |
| POST | `/documents/{id}/reprocess/` | Re-run pipeline |

## Tasks / Notifications

| Method | Endpoint |
|---|---|
| GET/POST | `/tasks/` |
| POST | `/tasks/{id}/complete/` |
| POST | `/tasks/{id}/set_status/` |
| GET | `/notifications/` |
| GET | `/notifications/unread/` |
| POST | `/notifications/{id}/mark_as_read/` |
| POST | `/notifications/mark_all_as_read/` |

## AI

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/ai/cases/{case_id}/chat/` | Get/create conversation |
| POST | `/ai/cases/{case_id}/chat/` | Ask question → `{answer, citations, sources, warnings}` |
| GET | `/ai/cases/{case_id}/explain/` | Case explanation (cached) |

## Analytics

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/analytics/admin/` | Admin stats, distributions, attention flags |
| GET | `/analytics/cause-list/` | Cause list (role-scoped) |
| GET | `/analytics/calendar/?start=&end=` | Calendar events |
| GET | `/analytics/cases/{id}/health/` | Case health indicators |
| GET | `/analytics/cases/{id}/what-changed/` | What changed since last visit |
| GET | `/analytics/cases/{id}/scheduling-suggestions/` | Suggested hearing dates |

## Courts

| Method | Endpoint |
|---|---|
| GET/POST | `/courts/` (admin-only writes) |
| GET/POST | `/courts/courtrooms/` (admin-only writes) |

## Public (guest, anonymous)

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/public/cases/` | Public search (number/CNR/party/type/court/date/status) |
| GET | `/public/cases/{id}/` | Public detail + public timeline |
| GET | `/public/cases/{id}/hearings/` | Public hearings |
| GET | `/public/cases/{id}/orders/` | Public published orders |
| GET | `/public/cases/{id}/documents/` | Public documents |
| GET | `/public/cases/{id}/next-hearing/` | Next public hearing |
