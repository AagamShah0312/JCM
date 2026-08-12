# AI Architecture

This project uses **Google Gemini** as the AI provider for case-aware features.
(The previous FreeLLMAPI service was removed from the repository.)

## Current flow

1. The React case detail page calls Django AI endpoints.
2. Django loads the selected case, related documents, and any prior conversation history.
3. The backend builds a case-specific prompt.
4. `services/ai_service.py` sends that prompt to the Google Gemini API using the
   `google-generativeai` SDK.
5. The AI response is returned as structured JSON to the frontend.

## Backend components

- `backend/services/ai_service.py`
  - Thin wrapper around the Gemini SDK (`ask_gemini`).
  - Reads `GEMINI_API_KEY` and `GEMINI_MODEL`.
  - Tries a fallback model list if the configured model is unavailable.
  - Returns a friendly setup message when no API key is configured, so the
    app never crashes without a key.
- `backend/apps/ai_assistant/services.py`
  - Builds case prompts.
  - Selects relevant documents.
  - Reuses `ask_gemini()` for chat, summary, explanation, and timeline generation.
- `backend/apps/ai_assistant/views.py`
  - Exposes API endpoints for case chat and case explanation.
  - Maintains conversation history in `AIConversation` and `AIMessage`.
  - Logs queries in `AIQuery`.

## Environment variables

- `GEMINI_API_KEY`
  - Your Google AI Studio key (https://aistudio.google.com/apikey).
  - Leave blank to disable the AI assistant gracefully.
- `GEMINI_MODEL`
  - Default: `gemini-2.5-flash`
  - Any model id supported by the Gemini API, e.g. `gemini-2.5-flash`,
    `gemini-2.0-flash`, `gemini-1.5-flash`.
- `OPENAI_API_KEY` / `USE_LOCAL_LLM` / `OLLAMA_BASE_URL`
  - Retained for future provider options; not used by the current Gemini path.

## Setup

```bash
cd JudicialCaseManagementSystem
cp .env.example .env   # then paste your key
# .env
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash

cd backend
pip install -r requirements.txt
python manage.py runserver
```

## Current AI endpoints

- `GET /api/ai/cases/<case_id>/chat/`
  - Returns or creates the conversation for the case.
  - Includes conversation metadata and full message history.
- `POST /api/ai/cases/<case_id>/chat/`
  - Sends a new message for the current case.
  - Returns the updated conversation, user message, assistant message, and sources.
- `GET /api/ai/cases/<case_id>/explain/`
  - Returns a simplified case explanation.
  - Uses cache keyed by case data and document freshness.
- Existing conversation endpoints remain available under `/api/ai/conversations/` for backward compatibility.

## Chatbot flow

1. The case detail page loads the case record.
2. The chatbot panel calls the case chat endpoint.
3. Django retrieves the conversation or creates it if it does not exist.
4. The backend includes:
   - case number
   - title
   - description
   - status
   - relevant documents
   - recent conversation history
5. The prompt is sent to Gemini through `ask_gemini()`.
6. The assistant message is stored and returned to the UI.

## Explanation caching

The "Explain Case" endpoint caches responses in Django cache using a key that includes:

- case ID
- case `updated_at`
- latest related document timestamp

That keeps repeated requests fast while still invalidating stale explanations when the case or documents change.

## Provider swap path

The prompt-building layer is provider-agnostic: to move to another provider,
replace the body of `ask_gemini()` in `backend/services/ai_service.py` and keep
the prompt builders and response contract unchanged.

## Notes

- The system does not need a new AI model layer.
- The important part is the prompt contract and the structured response shape.
- The current code keeps those two pieces isolated so provider migration stays local.
