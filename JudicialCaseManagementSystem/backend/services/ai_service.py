# services/ai_service.py
"""
AI service backed by Google Gemini (official `google-genai` SDK).

The old FreeLLMAPI wrapper was removed in favour of Gemini. Add your
GEMINI_API_KEY to the backend .env file to activate the AI features.

Usage:
    from services.ai_service import ask_gemini
    answer = ask_gemini("Explain this case in simple words")
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Default model used when GEMINI_MODEL is not set in the environment.
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'
# Fallbacks tried in order if the configured model is unavailable.
FALLBACK_GEMINI_MODELS = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']


def get_gemini_api_key() -> str:
    """Return the configured Gemini API key (may be empty)."""
    return (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()


def get_gemini_model() -> str:
    """Return the configured Gemini model name (with fallback)."""
    return (getattr(settings, 'GEMINI_MODEL', '') or '').strip() or DEFAULT_GEMINI_MODEL


def ask_gemini(prompt: str, model: str | None = None) -> str:
    """
    Send a prompt to Google Gemini and return the text response.

    - If no API key is configured, a friendly setup message is returned so the
      caller does not crash.
    - If a model name fails, the next model in the fallback list is tried.
    - On total failure a safe error string is returned.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return "[AI not configured] Add your GEMINI_API_KEY to the backend .env file to enable the AI assistant."

    try:
        from google import genai
    except ImportError:
        logger.error("google-genai is not installed")
        return "[AI error] Gemini SDK not installed. Run: pip install google-genai"

    client = genai.Client(api_key=api_key)

    # Build the list of models to try (deduplicated, in order).
    models_to_try = []
    for candidate in [model, get_gemini_model(), DEFAULT_GEMINI_MODEL, *FALLBACK_GEMINI_MODELS]:
        if candidate and candidate not in models_to_try:
            models_to_try.append(candidate)

    last_error: Exception | None = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (getattr(response, 'text', '') or '').strip()
            if text:
                return text
            logger.warning(f"Gemini model {model_name} returned an empty response")
        except Exception as exc:  # noqa: BLE001 - fall back to the next model
            last_error = exc
            logger.warning(f"Gemini model {model_name} failed: {exc}")

    return f"[AI error] Unable to produce a response from Gemini: {last_error}"
