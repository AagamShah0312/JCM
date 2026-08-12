"""
Embedding helpers: vectorize text and compute similarity.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_embedding_dimension() -> int:
    return int(getattr(settings, 'VECTOR_EMBEDDING_DIM', 768))


def embed_texts(texts, model=None):
    """Embed a list of texts using the configured AI provider."""
    from apps.ai.providers import get_ai_provider
    provider = get_ai_provider()
    model = model or settings.AI_EMBEDDING_MODEL
    return provider.embed_texts(texts, model=model)


def embed_text(text, model=None):
    vectors = embed_texts([text], model=model)
    return vectors[0] if vectors else []


def cosine_similarity(a, b):
    """Cosine similarity between two vectors (plain Python fallback)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
