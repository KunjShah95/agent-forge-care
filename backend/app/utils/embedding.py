"""
Embedding utilities for the AgentForge memory layer.

Provides text-to-vector embedding using a multi-provider fallback chain:
1. OpenAI text-embedding-3-small (preferred, 1536 dimensions)
2. Google Gemini text-embedding-004 (768 dimensions)
3. HuggingFace sentence-transformers (free, local, 768 dimensions)
4. Ollama nomic-embed-text (free, local, 768 dimensions)
5. Simple hash-based fallback (for development/demo only)

Uses the AI Model Manager for provider discovery and fallback.
"""

import hashlib
import logging

import numpy as np

from app.services.model_manager import get_embeddings

logger = logging.getLogger("agentforge.embeddings")

# Cache for the LangChain embeddings instance
_embeddings_instance: object | None = None


async def get_text_embedding(text: str) -> list[float]:
    """
    Get embedding vector for a text string.
    Uses the best available embedding provider from the multi-provider chain.
    Falls back to hash-based deterministic embeddings when no provider is available.
    """
    global _embeddings_instance

    if _embeddings_instance:
        try:
            return await _do_embedding(_embeddings_instance, text)
        except Exception as e:
            logger.warning("Cached embeddings failed, reinitializing: %s", e)
            _embeddings_instance = None

    # Get from model manager
    _embeddings_instance = get_embeddings()

    if _embeddings_instance:
        try:
            return await _do_embedding(_embeddings_instance, text)
        except Exception as e:
            logger.warning("Embedding failed, using hash fallback: %s", e)
            return _get_fallback_embedding(text)

    # No embedding provider available — use deterministic fallback
    return _get_fallback_embedding(text)


async def _do_embedding(embeddings, text: str) -> list[float]:
    """Execute embedding with the given provider instance."""
    # Truncate long texts to avoid token limits
    max_chars = 8000
    truncated = text[:max_chars]

    result = await embeddings.aembed_query(truncated)
    return result


def _get_fallback_embedding(text: str, dimensions: int = 384) -> list[float]:
    """
    Deterministic fallback embedding using hash-based vector generation.
    For development/demo purposes only — replace with a real model in production.
    """
    # Normalize text
    text = text.lower().strip()

    # Create a seed from text hash
    hash_bytes = hashlib.sha256(text.encode()).digest()

    # Generate deterministic vector using numpy
    seed_val = int.from_bytes(hash_bytes[:4], "big")
    rng = np.random.RandomState(seed_val)
    vector = rng.randn(dimensions).astype(np.float32)

    # Normalize to unit length
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def compute_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def clear_embedding_cache():
    """Clear the cached embeddings instance (e.g., for testing)."""
    global _embeddings_instance
    _embeddings_instance = None
