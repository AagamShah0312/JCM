"""
AI provider abstraction (spec §35).

The application talks to a common AIProvider interface. The active provider
is chosen via the AI_PROVIDER env var:
  - gemini   (default)
  - openai
  - anthropic
  - local

Each provider implements:
  - chat(messages, system=None, temperature=..., max_tokens=...) -> str
  - embed_texts(texts, model=...) -> list[list[float]]

API keys are read from settings (environment variables), never hard-coded.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    pass


class BaseAIProvider:
    name = 'base'

    def chat(self, messages, system=None, temperature=None, max_tokens=None) -> str:
        raise NotImplementedError

    def embed_texts(self, texts, model=None):
        raise NotImplementedError


class GeminiProvider(BaseAIProvider):
    """Google Gemini via the official google-genai SDK."""

    name = 'gemini'

    def __init__(self):
        self.api_key = (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
        self.chat_model = getattr(settings, 'AI_CHAT_MODEL', '') or 'gemini-2.5-flash'
        self.embed_model = getattr(settings, 'AI_EMBEDDING_MODEL', '') or 'gemini-embedding-001'
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise AIProviderError("google-genai SDK not installed") from exc
            if not self.api_key:
                raise AIProviderError("GEMINI_API_KEY is not configured")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def chat(self, messages, system=None, temperature=None, max_tokens=None) -> str:
        try:
            contents = []
            if system:
                contents.append(system)
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    contents.append(f"[SYSTEM] {content}")
                elif role == 'assistant':
                    contents.append(f"[ASSISTANT] {content}")
                else:
                    contents.append(f"[USER] {content}")
            prompt = '\n\n'.join(contents)
            config = {}
            if temperature is not None:
                config['temperature'] = temperature
            if max_tokens is not None:
                config['max_output_tokens'] = max_tokens
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(**config) if config else None,
            )
            text = (getattr(response, 'text', '') or '').strip()
            if not text:
                raise AIProviderError("Gemini returned empty response")
            return text
        except Exception as exc:
            if isinstance(exc, AIProviderError):
                raise
            raise AIProviderError(f"Gemini chat failed: {exc}") from exc

    def embed_texts(self, texts, model=None):
        """Gemini embeddings API. Returns list of float vectors."""
        try:
            model = model or self.embed_model
            result = self.client.models.embed_content(
                model=model,
                contents=texts,
            )
            embeddings = [item.values for item in result.embeddings]
            return embeddings
        except Exception as exc:
            raise AIProviderError(f"Gemini embed failed: {exc}") from exc


class OpenAIProvider(BaseAIProvider):
    """OpenAI-compatible provider (configurable base URL / key)."""

    name = 'openai'

    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
        self.chat_model = getattr(settings, 'AI_CHAT_MODEL', '') or 'gpt-4o-mini'
        self.base_url = getattr(settings, 'OPENAI_BASE_URL', None)

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError("openai SDK not installed") from exc
        if not self.api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")
        kwargs = {'api_key': self.api_key}
        if self.base_url:
            kwargs['base_url'] = self.base_url
        return OpenAI(**kwargs)

    def chat(self, messages, system=None, temperature=None, max_tokens=None) -> str:
        try:
            msgs = ([{'role': 'system', 'content': system}] if system else []) + list(messages)
            kwargs = {'model': self.chat_model, 'messages': msgs}
            if temperature is not None:
                kwargs['temperature'] = temperature
            if max_tokens is not None:
                kwargs['max_tokens'] = max_tokens
            resp = self._client().chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or '').strip()
        except Exception as exc:
            raise AIProviderError(f"OpenAI chat failed: {exc}") from exc

    def embed_texts(self, texts, model=None):
        try:
            model = model or 'text-embedding-3-small'
            resp = self._client().embeddings.create(model=model, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as exc:
            raise AIProviderError(f"OpenAI embed failed: {exc}") from exc


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider (interface stub — requires anthropic SDK)."""

    name = 'anthropic'

    def __init__(self):
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''
        self.chat_model = getattr(settings, 'AI_CHAT_MODEL', '') or 'claude-3-5-haiku-latest'

    def chat(self, messages, system=None, temperature=None, max_tokens=None) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise AIProviderError("anthropic SDK not installed") from exc
        if not self.api_key:
            raise AIProviderError("ANTHROPIC_API_KEY is not configured")
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {'model': self.chat_model, 'max_tokens': max_tokens or 2048, 'messages': messages}
            if system:
                kwargs['system'] = system
            if temperature is not None:
                kwargs['temperature'] = temperature
            resp = client.messages.create(**kwargs)
            return ''.join(block.text for block in resp.content if getattr(block, 'type', '') == 'text').strip()
        except Exception as exc:
            raise AIProviderError(f"Anthropic chat failed: {exc}") from exc

    def embed_texts(self, texts, model=None):
        raise AIProviderError("Anthropic embeddings not supported by provider interface")


class LocalProvider(BaseAIProvider):
    """
    Local/self-hosted provider (e.g. Ollama). Uses an OpenAI-compatible
    endpoint via the openai SDK pointed at a local base URL.
    """

    name = 'local'

    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434/v1')
        self.chat_model = getattr(settings, 'AI_CHAT_MODEL', '') or 'llama3'

    def chat(self, messages, system=None, temperature=None, max_tokens=None) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError("openai SDK not installed") from exc
        try:
            client = OpenAI(base_url=self.base_url, api_key='local')
            msgs = ([{'role': 'system', 'content': system}] if system else []) + list(messages)
            kwargs = {'model': self.chat_model, 'messages': msgs}
            if temperature is not None:
                kwargs['temperature'] = temperature
            if max_tokens is not None:
                kwargs['max_tokens'] = max_tokens
            resp = client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or '').strip()
        except Exception as exc:
            raise AIProviderError(f"Local provider chat failed: {exc}") from exc

    def embed_texts(self, texts, model=None):
        # Local embedding: not configured — raise so callers degrade gracefully.
        raise AIProviderError("Local embeddings not configured; set AI_EMBEDDING_MODEL to a remote provider")


class AIProviderFactory:
    _instances = {}

    @classmethod
    def get(cls, name=None):
        name = name or getattr(settings, 'AI_PROVIDER', 'gemini')
        if name not in cls._instances:
            providers = {
                'gemini': GeminiProvider,
                'openai': OpenAIProvider,
                'anthropic': AnthropicProvider,
                'local': LocalProvider,
            }
            provider_cls = providers.get(name)
            if not provider_cls:
                raise AIProviderError(f"Unknown AI provider: {name}")
            cls._instances[name] = provider_cls()
        return cls._instances[name]


def get_ai_provider(name=None) -> BaseAIProvider:
    return AIProviderFactory.get(name)
