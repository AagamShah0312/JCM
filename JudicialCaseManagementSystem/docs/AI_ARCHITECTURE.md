# AI Architecture

This project uses the existing FreeLLMAPI service as the active AI provider for case-aware features.

## Current flow

1. The React case detail page calls Django AI endpoints.
2. Django loads the selected case, related documents, and any prior conversation history.
3. The backend builds a case-specific prompt.
4. `services/ai_service.py` sends that prompt to FreeLLMAPI at `http://localhost:3001/v1/chat/completions`.
5. The AI response is returned as structured JSON to the frontend.

## Backend components

- `backend/services/ai_service.py`
  - Thin HTTP wrapper around FreeLLMAPI.
  - Reads `AI_API_URL` and `AI_API_KEY`.
- `backend/apps/ai_assistant/services.py`
  - Builds case prompts.
  - Selects relevant documents.
  - Reuses `ask_ai()` for chat, summary, explanation, and timeline generation.
- `backend/apps/ai_assistant/views.py`
  - Exposes API endpoints for case chat and case explanation.
  - Maintains conversation history in `AIConversation` and `AIMessage`.
  - Logs queries in `AIQuery`.

## Environment variables

- `AI_API_URL`
  - Default: `http://localhost:3001/v1`
  - Base URL for FreeLLMAPI.
- `AI_API_KEY`
  - Sent as the bearer token to FreeLLMAPI.
- `OPENAI_API_KEY`
  - Kept for migration compatibility.
- `USE_LOCAL_LLM`
  - Retained from the existing RAG code path.
- `OLLAMA_BASE_URL`
  - Retained for the same reason.

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
5. The prompt is sent to FreeLLMAPI through `ask_ai()`.
6. The assistant message is stored and returned to the UI.

## Explanation caching

The "Explain Case" endpoint caches responses in Django cache using a key that includes:

- case ID
- case `updated_at`
- latest related document timestamp

That keeps repeated requests fast while still invalidating stale explanations when the case or documents change.

## Future migration paths

The current prompt-building layer is provider-agnostic enough to swap the transport later.

### Gemini Direct API

- Replace the body of `ask_ai()` with a direct Gemini client call.
- Keep the prompt builders and response contract unchanged.

### OpenAI API

- Restore the OpenAI request implementation inside `ask_ai()`.
- Keep the case prompt builders and the frontend untouched.

### OpenRouter

- Point `AI_API_URL` at the OpenRouter-compatible endpoint.
- Preserve the same backend JSON contract and conversation storage.

## Notes

- The system does not need a new AI model layer.
- The important part is the prompt contract and the structured response shape.
- The current code keeps those two pieces isolated so provider migration stays local.
