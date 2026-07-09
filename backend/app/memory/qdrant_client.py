"""
Qdrant vector database client for AgentForge memory layer.

Stores embeddings for:
- Resume text → resume_embeddings collection
- Job/opportunity descriptions → opportunity_embeddings collection
- Skill vectors → skill_embeddings collection
- Interview notes → memory_notes collection
"""

import logging
import uuid

from qdrant_client import QdrantClient as QdrantRawClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger("agentforge.qdrant")

# Embedding dimension (multi-provider support).
# Used by: HuggingFace (768), Ollama nomic-embed-text (768), Gemini (768),
# OpenAI text-embedding-3-small (1536), OpenAI text-embedding-3-large (3072).
# Default: 768 (works with HuggingFace, Ollama, Gemini — most common)
# When OpenAI is the active provider, pass 1536 explicitly.
DEFAULT_EMBEDDING_SIZE = 768

COLLECTIONS = {
    "resume_embeddings": VectorParams(size=DEFAULT_EMBEDDING_SIZE, distance=Distance.COSINE),
    "opportunity_embeddings": VectorParams(size=DEFAULT_EMBEDDING_SIZE, distance=Distance.COSINE),
    "skill_embeddings": VectorParams(size=DEFAULT_EMBEDDING_SIZE, distance=Distance.COSINE),
    "memory_notes": VectorParams(size=DEFAULT_EMBEDDING_SIZE, distance=Distance.COSINE),
    "research_notes": VectorParams(size=DEFAULT_EMBEDDING_SIZE, distance=Distance.COSINE),
}


def get_qdrant_client() -> QdrantRawClient:
    """Get or create a Qdrant client connection."""
    return QdrantRawClient(
        url=settings.qdrant_url,
        timeout=30,
    )


def gen_point_id() -> str:
    return str(uuid.uuid4())


def init_collections():
    """Initialize all required collections if they don't exist. Synchronous call."""
    try:
        client = get_qdrant_client()
        existing = client.get_collections().collections
        existing_names = {c.name for c in existing}

        for name, params in COLLECTIONS.items():
            if name not in existing_names:
                client.create_collection(
                    collection_name=name,
                    vectors_config=params,
                )
                logger.info("Created Qdrant collection: %s", name)

        client.close()
    except Exception as e:
        logger.warning("Qdrant not available at %s: %s", settings.qdrant_url, e)
