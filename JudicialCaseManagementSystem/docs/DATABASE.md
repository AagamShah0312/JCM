# JCM Database Schema

PostgreSQL 15+ with the `vector` (pgvector) and `pg_trgm` extensions.

## Core entities

```
authentication_user          — custom User (email login, role, professional_id)
authentication_judgeprofile  — judge professional profile
authentication_lawyerprofile — lawyer professional profile

courts_court                 — court (name, type, state, city)
courts_courtroom             — courtroom within a court

cases_case                   — the case hub (see below)
cases_caseparty              — multiple petitioners/respondents
cases_caselawyer             — lawyer links to a case (role, active)
cases_caseevent              — unified clickable timeline
cases_casestatushistory      — append-only status transitions
cases_casestatusoption       — configurable statuses
cases_caseassignment         — legacy lawyer assignment
cases_casenote               — case notes

hearings_hearing             — first-class hearing (number, date, status, adjournment)
hearings_hearingparticipant  — attendance
hearings_hearingproceeding   — proceedings of a hearing
hearings_adjournmentreasonoption — configurable adjournment reasons

orders_order                 — order (draft/signed/published/superseded)
orders_orderversion          — append-only order versions

documents_casedocument       — document metadata (visibility, processing state, checksum, storage key)
documents_documentversion    — append-only versions
documents_documentextraction — extracted text + page metadata
documents_documentaccess     — explicit per-user grants
documents_documentchunk      — searchable chunks with pgvector embedding

tasks_task                   — work items (case/hearing/document linked)

notifications_notification   — in-app notifications

ai_assistant_aiconversation  — AI chat per (case, user)
ai_assistant_aimessage       — messages with sources
ai_assistant_aicitation      — clickable source references
ai_assistant_aiquery         — query log
ai_assistant_documentembedding — (legacy)

audit_auditlog               — append-only audit trail
```

## `cases_case` key columns

| Column | Purpose |
|---|---|
| `case_number` / `cnr_number` | unique identifiers |
| `status` | FILED/REGISTERED/PENDING/ACTIVE/ADJOURNED/RESERVED_FOR_ORDER/DISPOSED/TRANSFERRED/CLOSED |
| `priority` | URGENT/HIGH/NORMAL/LOW |
| `court` / `courtroom` | FKs to courts |
| `assigned_judge` / `assigned_lawyer` | FKs to users |
| `filing_date` / `registration_date` / `disposal_date` | lifecycle dates |
| `is_public` | guest visibility flag |
| `is_archived` / `deleted_at` / `deleted_by` | soft delete |

## Document visibility

`PUBLIC`, `LAWYER_ONLY`, `JUDGE_ONLY`, `RESTRICTED`, `ADMIN_ONLY`.

## Document processing states

`UPLOADED`, `PROCESSING`, `PROCESSED`, `OCR_REQUIRED`, `OCR_COMPLETED`, `FAILED`.

## Embeddings

`documents_documentchunk.embedding` is a `vector(768)` pgvector column.
Created by migration `documents/0004` which also runs
`CREATE EXTENSION IF NOT EXISTS vector`.

## Indexes

Cases: case_number, cnr_number, status, court, assigned_judge, assigned_lawyer,
filing_date, next_hearing_date, case_type, priority, created_at.
Hearings: (case, date), date, (judge, date), status.
Orders: (case, date), date, status.
Documents: (case, document_type), (case, hearing), visibility, processing_state.
Chunks: (document, chunk_index), case, page_number.
Audit: (user, created_at), (action, created_at), (model_name, object_id).

## Deletion policy

Judicial records are never hard-deleted casually:
- Cases: soft archive (`is_archived`, `deleted_at`, `deleted_by`).
- Documents: state `DELETED` (history preserved).
- Orders/hearings: status-based lifecycle, versions preserved.
- Audit logs: append-only (`delete()` raises NotImplementedError).
