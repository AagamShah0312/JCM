# Judicial Case Management System

A Django REST Framework and React application for court case management, hearing tracking, document uploads, legal history, and a case-aware AI assistant.

## Current Features

- Role-based access for admin, judge, lawyer, and guest users.
- Admins can create, edit, finish, and delete cases.
- Judges can create cases and update hearing dates for their assigned or created cases.
- Lawyers and guests can view cases, hearings, documents, and legal history.
- Judges and admins can upload one or more documents when creating a case, from case details, or while updating a hearing.
- Document labels include statement, bonafide document, petition, affidavit, judgment, order, evidence, and other.
- Admins can upload `Judge.csv` and `Lawyer.csv`, promote or demote users, and manage staff IDs.
- Cases support assigned judge IDs, assigned lawyer IDs, and an optional public interest live link.
- Analytics show past cases, active/closed totals, recorded wins, and win percentage for judges and lawyers.
- AI assistant reads extracted text from uploaded documents and images when OCR dependencies are available.
- AI assistant can answer general questions, but avoids direct verdicts or opinions on who should win a case.

### Gemini API Key

The AI assistant uses Google Gemini. Get a free API key at
https://aistudio.google.com/apikey and add it to the backend environment:

```bat
:: JudicialCaseManagementSystem\.env  (copy from .env.example)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

The AI features work without running any extra service — the backend talks to
Gemini directly through the `google-generativeai` SDK.

## Run Locally

Open two terminals.

### Backend

```bat
cd JudicialCaseManagementSystem\backend
C:/Users/cebc/anaconda3/Scripts/activate
python manage.py migrate
python manage.py runserver
```

Backend API: `http://localhost:8000/api`

### Frontend

```bat
cd JudicialCaseManagementSystem\frontend
npm install
npm start
```

Main app: `http://localhost:3000`

## CSV Import Format

Admins can upload staff CSV files from the Staff Admin page.

`Judge.csv` or `Lawyer.csv` should contain:

```csv
id,email,first_name,last_name
J-100,judge@example.com,Asha,Mehta
L-100,lawyer@example.com,Ravi,Shah
```

Accepted ID headers are `id`, `unique_id`, or `professional_id`. Imported users get the selected role and are marked verified.

## Main API Areas

- `POST /api/auth/users/import_staff_csv/` imports judges or lawyers from CSV.
- `POST /api/auth/users/{id}/promote_demote/` changes a user's role or staff ID.
- `GET /api/auth/users/{id}/analytics/` returns legal history and win stats.
- `GET /api/cases/` lists cases visible to the current role.
- `POST /api/cases/` creates cases for admins and judges.
- `PATCH /api/cases/{id}/` updates cases for admins and assigned judges.
- `DELETE /api/cases/{id}/` deletes cases for admins only.
- `POST /api/cases/{id}/update_hearing/` updates hearing dates and can upload hearing documents.
- `POST /api/documents/` uploads one or more case documents.
- `GET /api/documents/{id}/extraction/` returns extracted document text.
- `GET /api/ai/cases/{case_id}/chat/` opens case AI chat.
- `POST /api/ai/cases/{case_id}/chat/` sends a case-aware or general AI prompt.

## Testing

```bat
cd JudicialCaseManagementSystem\backend
C:/Users/cebc/anaconda3/Scripts/activate
python manage.py test
```

The test suite includes coverage for judge case creation, admin-only deletion, hearing document upload and extraction, CSV staff import, promotion/demotion, and guest read-only access.

## Project Structure

```text
JudicialCaseManagementSystem/
  backend/
    apps/
      authentication/
      cases/
      documents/
      ai_assistant/
      notifications/
      audit/
    judicial_backend/
    manage.py
  frontend/
    src/
      components/
      context/
      pages/
      services/
      styles/
  docs/
  docker/
```
