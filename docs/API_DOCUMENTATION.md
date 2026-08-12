# Judicial Case Management System - API Documentation

## Authentication API

### Register User
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "role": "lawyer"
}

Response: 201 Created
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "lawyer"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Login User
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response: 200 OK
{
  "user": { ... },
  "access": "...",
  "refresh": "..."
}
```

### Get Profile
```http
GET /api/auth/profile/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "lawyer",
  "is_verified": true,
  "created_at": "2026-05-31T13:15:39Z"
}
```

## Cases API

### List Cases
```http
GET /api/cases/?page=1&page_size=10&status=active&search=2025-ABC
Authorization: Bearer <access_token>

Response: 200 OK
{
  "count": 5,
  "next": "http://...",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "case_number": "2025-ABC-101",
      "title": "John vs Jane",
      "status": "active",
      "next_hearing_date": "2026-06-15",
      "plaintiff_name": "John Smith",
      "defendant_name": "Jane Doe",
      "created_at": "2026-05-31T13:15:39Z"
    }
  ]
}
```

### Create Case
```http
POST /api/cases/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "case_number": "2025-ABC-102",
  "title": "Corporate Dispute",
  "description": "Detailed case description...",
  "court_name": "District Court",
  "case_type": "Corporate",
  "filing_date": "2026-05-15",
  "next_hearing_date": "2026-06-15",
  "plaintiff_name": "Company A",
  "defendant_name": "Company B",
  "judge_name": "Justice Smith"
}

Response: 201 Created
{ ... case object ... }
```

### Get Case Details
```http
GET /api/cases/{case_id}/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "uuid",
  "case_number": "2025-ABC-101",
  "title": "John vs Jane",
  "description": "...",
  "status": "active",
  "court_name": "District Court",
  "filing_date": "2026-05-15",
  "next_hearing_date": "2026-06-15",
  "judge_name": "Justice Smith",
  "plaintiff_name": "John Smith",
  "defendant_name": "Jane Doe",
  "timeline_events": [ ... ],
  "documents": [ ... ],
  "notes_count": 3,
  "created_by": { ... },
  "created_at": "2026-05-31T13:15:39Z"
}
```

### Update Case
```http
PUT /api/cases/{case_id}/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "closed",
  "next_hearing_date": null
}

Response: 200 OK
{ ... updated case object ... }
```

### Delete Case
```http
DELETE /api/cases/{case_id}/
Authorization: Bearer <access_token>

Response: 204 No Content
```

### Get Case Timeline
```http
GET /api/cases/{case_id}/timeline/
Authorization: Bearer <access_token>

Response: 200 OK
[
  {
    "id": "uuid",
    "event_type": "hearing",
    "event_description": "Preliminary hearing",
    "event_date": "2026-05-15",
    "notes": "..."
  }
]
```

### Add Timeline Event
```http
POST /api/cases/{case_id}/add_timeline_event/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event_type": "judgment",
  "event_description": "Final judgment delivered",
  "event_date": "2026-06-15",
  "notes": "Case decided in favor of plaintiff"
}

Response: 201 Created
{ ... timeline event object ... }
```

## Documents API

### Upload Document
```http
POST /api/documents/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

form-data:
- case: "case-uuid"
- document_type: "petition"
- file: <file>
- description: "Petition document"

Response: 201 Created
{
  "id": "uuid",
  "case": "case-uuid",
  "document_type": "petition",
  "file_name": "petition.pdf",
  "file_size": 102400,
  "uploaded_by": "user@example.com",
  "description": "Petition document",
  "uploaded_at": "2026-05-31T13:15:39Z"
}
```

### Download Document
```http
GET /api/documents/{document_id}/download/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "download_url": "http://...document.pdf",
  "file_name": "petition.pdf"
}
```

### Get Document Extraction
```http
GET /api/documents/{document_id}/extraction/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "uuid",
  "extracted_text": "Full text from document...",
  "ocr_text": "...",
  "metadata": {
    "author": "...",
    "date": "..."
  },
  "extracted_at": "2026-05-31T13:15:39Z"
}
```

## AI Assistant API

### Create Conversation
```http
POST /api/ai/conversations/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "case": "case-uuid"
}

Response: 201 Created
{
  "id": "uuid",
  "case": "case-uuid",
  "title": null,
  "created_at": "2026-05-31T13:15:39Z"
}
```

### Send Message
```http
POST /api/ai/conversations/{conversation_id}/send_message/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Explain the key points of this case in simple language"
}

Response: 201 Created
{
  "conversation": { ... },
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Explain the key points...",
      "created_at": "2026-05-31T13:15:39Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "The case involves... [AI-generated response]",
      "tokens_used": 250,
      "created_at": "2026-05-31T13:15:39Z"
    }
  ]
}
```

### Summarize Case
```http
POST /api/ai/conversations/{conversation_id}/summarize/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "summary": "This case involves a dispute between... The key issues are... The likely outcome...",
  "tokens_used": 500,
  "processing_time": 2.5
}
```

### Generate Timeline
```http
POST /api/ai/conversations/{conversation_id}/generate_timeline/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "timeline": [
    {
      "date": "2026-05-01",
      "event": "Case filed",
      "description": "Initial petition submitted"
    },
    {
      "date": "2026-05-15",
      "event": "First hearing",
      "description": "Preliminary hearing conducted"
    }
  ],
  "tokens_used": 400,
  "processing_time": 1.8
}
```

### Case-Aware Chat
```http
GET /api/ai/cases/{case_id}/chat/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "case": {
    "id": "uuid",
    "case_number": "2025-ABC-101",
    "title": "John vs Jane"
  },
  "conversation": {
    "id": "uuid",
    "case": "case-uuid",
    "case_number": "2025-ABC-101",
    "case_title": "John vs Jane",
    "messages": []
  },
  "messages": []
}
```

```http
POST /api/ai/cases/{case_id}/chat/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Explain the current status of this case in simple language."
}

Response: 201 Created
{
  "case": { ... },
  "conversation": { ... },
  "user_message": { ... },
  "assistant_message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Simple case explanation...",
    "sources": [
      {
        "doc_id": "uuid",
        "file_name": "petition.pdf",
        "document_type": "petition"
      }
    ]
  },
  "messages": [ ... ],
  "sources": [ ... ]
}
```

### Case Explanation
```http
GET /api/ai/cases/{case_id}/explain/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "case": {
    "id": "uuid",
    "case_number": "2025-ABC-101",
    "title": "John vs Jane",
    "status": "active"
  },
  "explanation": "Plain-language explanation of the case...",
  "sources": [
    {
      "doc_id": "uuid",
      "file_name": "petition.pdf",
      "document_type": "petition"
    }
  ],
  "generated_at": "2026-06-04T10:00:00Z",
  "processing_time": 1.24,
  "cached": false
}
```

## Notifications API

### List Notifications
```http
GET /api/notifications/?page=1&is_read=false
Authorization: Bearer <access_token>

Response: 200 OK
{
  "results": [
    {
      "id": "uuid",
      "title": "Case Assigned",
      "message": "You have been assigned to case 2025-ABC-101",
      "notification_type": "case_assigned",
      "is_read": false,
      "created_at": "2026-05-31T13:15:39Z"
    }
  ]
}
```

### Mark as Read
```http
POST /api/notifications/{notification_id}/mark_as_read/
Authorization: Bearer <access_token>

Response: 200 OK
{ "status": "marked as read" }
```

## Query Parameters

### Pagination
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)

### Filtering
- `status`: Filter by case status (pending, active, closed, appealed)
- `court_name`: Filter by court name
- `case_type`: Filter by case type
- `is_read`: Filter notifications (true/false)
- `notification_type`: Filter by notification type

### Search
- `search`: Full-text search across multiple fields

### Ordering
- `ordering`: Order by field (e.g., `-created_at`)

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1234567890
```

## Authentication Headers

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

## Content Types

Supported:
- `application/json`
- `multipart/form-data` (for file uploads)
- `application/x-www-form-urlencoded`

---

For more examples and detailed information, see the Postman collection or contact support.
