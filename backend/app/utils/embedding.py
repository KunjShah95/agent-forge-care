"""
Embedding utilities for the AgentForge memory layer.

Provides text-to-vector embedding using:
1. OpenAI's text-embedding-3-small (preferred, 1536 dimensions)
2. Or a simple hash-based fallback for development
"""

import logging
import hashlib
import numpy as np
from typing import Optional

from app.config import settings

logger = logging.getLogger("agentforge.embeddings")


def get_text_embedding(text: str) -> list[float]:
    """
    Get embedding vector for a text string.
    Uses OpenAI if API key is available, otherwise uses a deterministic fallback.
    """
    if settings.openai_api_key:
        try:
            return _get_openai_embedding(text)
        except Exception as e:
            logger.warning("OpenAI embedding failed, using fallback: %s", e)
            return _get_fallback_embedding(text)
    else:
        return _get_fallback_embedding(text)


def _get_openai_embedding(text: str) -> list[float]:
    """Get embedding using OpenAI API."""
    import openai
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # Truncate to token limit
    )
    return response.data[0].embedding


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
    np.random.seed(int.from_bytes(hash_bytes[:4], "big"))
    vector = np.random.randn(dimensions).astype(np.float32)

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
