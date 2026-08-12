# Database Schema

This document summarizes the primary database models and relationships for the Judicial Case Management System.

## Users
- Table: authentication_user
- Fields: id (UUID), username, email, password, role (admin/lawyer), first_name, last_name, phone_number, profile_image, is_verified, created_at, updated_at
- Notes: Custom user model inheriting from AbstractUser. Email is unique.

## Cases
- Table: cases_case
- Fields: id (UUID), case_number (unique), title, description, court_name, case_type, filing_date, next_hearing_date, status, judge_name, plaintiff_name, defendant_name, assigned_lawyer (FK -> authentication_user), created_by (FK -> authentication_user), created_at, updated_at
- Indexes: case_number, status, assigned_lawyer

## CaseTimeline
- Table: cases_casetimeline
- Fields: id (UUID), case (FK -> cases_case), event_type, event_description, event_date, notes, created_by (FK -> authentication_user), created_at, updated_at

## CaseDocuments
- Table: documents_casedocument
- Fields: id (UUID), case (FK -> cases_case), document_type, file_name, file (file path), file_size, uploaded_by (FK -> authentication_user), description, uploaded_at, updated_at

## DocumentVersion
- Table: documents_documentversion
- Fields: id (UUID), document (FK -> documents_casedocument), version_number, file, uploaded_by, change_description, created_at

## DocumentExtraction
- Table: documents_documentextraction
- Fields: id (UUID), document (OneToOne -> documents_casedocument), extracted_text, ocr_text, metadata (JSON), extracted_at

## Notifications
- Table: notifications_notification
- Fields: id (UUID), user (FK -> authentication_user), notification_type, title, message, case (FK -> cases_case), is_read, action_url, created_at, updated_at

## AuditLog
- Table: audit_auditlog
- Fields: id (UUID), user (FK -> authentication_user), action, model_name, object_id, changes (JSON), ip_address, user_agent, status_code, created_at

## AI Assistant
- Tables:
  - ai_assistant_aiconversation
  - ai_assistant_aimessage
  - ai_assistant_audioquery
  - ai_assistant_documentembedding
- Fields (summary): store conversation metadata, messages with role and content, AI queries and responses, document embeddings for RAG

## Relationships
- User (1) <-> (M) Case (created_by)
- User (1) <-> (M) Case (assigned_lawyer)
- Case (1) <-> (M) CaseTimeline
- Case (1) <-> (M) CaseDocument
- CaseDocument (1) <-> (1) DocumentExtraction
- Case (1) <-> (M) Notification

## Notes
- All primary keys are UUID fields for security and easier distribution
- Several fields have GIN/GIST indexes where full-text search is intended
- Embeddings are stored as binary blobs and can be moved to vector DB (FAISS/Pinecone) for production
