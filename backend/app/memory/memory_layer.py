"""
Memory Layer — combines Qdrant vector search with PostgreSQL memory entries.

Provides a unified interface for storing and retrieving:
- User profile memory (skills, preferences, goals)
- Semantic search over opportunities and notes
- Context assembly for agent execution
"""

import logging
import uuid

from app.services.rerank_service import get_reranker

logger = logging.getLogger("agentforge.memory")


# Lazy imports for Qdrant — not installed in test/dev environments
def _get_qdrant_client():
    """Get the Qdrant client, returning None if not available."""
    try:
        from app.memory.qdrant_client import get_qdrant_client as _client

        return _client()
    except Exception as e:
        logger.debug("Qdrant client unavailable: %s", e)
        return None


def _get_point_types():
    """Get Qdrant model types, returning None if not available."""
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

        return PointStruct, Filter, FieldCondition, MatchValue  # noqa: N806
    except Exception:
        return None, None, None, None


class AgentMemory:
    """High-level memory interface for the agent system."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client = None
        self._connect()

    def _connect(self):
        """Connect to Qdrant if available."""
        self.client = _get_qdrant_client()

    def _get_filter(self, collection: str = ""):
        """Create a filter for the current user."""
        PointStruct, Filter, FieldCondition, MatchValue = _get_point_types() or (None, None, None, None)  # noqa: N806
        if Filter and FieldCondition and MatchValue:  # noqa: N806
            return Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=self.user_id))])  # noqa: N806
        return None

    # ─── Vector Storage ───────────────────────────────────

    def store_vector(
        self,
        collection: str,
        text: str,
        vector: list[float],
        metadata: dict | None = None,
    ):
        """Store a vector embedding with metadata."""
        if not self.client:
            return

        types = _get_point_types()
        if not types[0]:
            return
        point_struct_cls = types[0]

        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{collection}:{text[:1000]}"))

        payload = {
            "user_id": self.user_id,
            "text": text[:5000],
            **(metadata or {}),
        }

        self.client.upsert(
            collection_name=collection,
            points=[
                point_struct_cls(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def search_vectors(
        self,
        collection: str,
        vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.5,
    ):
        """Search for similar vectors in a collection."""
        if not self.client:
            return []

        types = _get_point_types()
        if types[1]:
            filter_cls, field_condition_cls, match_value_cls = types[1], types[2], types[3]
            query_filter = filter_cls(must=[field_condition_cls(key="user_id", match=match_value_cls(value=self.user_id))])
        else:
            query_filter = None

        return self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )

    def delete_user_vectors(self, collection: str):
        """Delete all vectors for this user in a collection."""
        if not self.client:
            return

        types = _get_point_types()
        if types[1] and types[2] and types[3]:
            filter_cls, field_condition_cls, match_value_cls = types[1], types[2], types[3]
            self.client.delete(
                collection_name=collection,
                points_selector=filter_cls(must=[field_condition_cls(key="user_id", match=match_value_cls(value=self.user_id))]),
            )

    def search_vectors_reranked(
        self,
        collection: str,
        query_vector: list[float],
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.5,
    ):
        """
        Search vectors in a collection, then rerank results with Cohere.

        Stage 1: Qdrant cosine similarity (fast recall)
        Stage 2: Cohere rerank (precision re-scoring)

        Returns reranked results with added 'relevance_score' field.
        Falls back to Qdrant-only results if Cohere is unavailable.
        """
        # Stage 1: Qdrant vector search
        results = self.search_vectors(collection, query_vector, limit, score_threshold)
        if not results:
            return []

        # Convert Qdrant results to document format for reranking
        documents = []
        for r in results:
            payload = r.payload if hasattr(r, "payload") else {}
            documents.append(
                {
                    "title": payload.get("title", "Untitled"),
                    "company": payload.get("company", ""),
                    "description": payload.get("text", "")[:500],
                    "match_score": payload.get("match_score", 0),
                    "_qdrant_score": r.score if hasattr(r, "score") else 0,
                    "_payload": payload,
                }
            )

        # Stage 2: Cohere rerank
        reranker = get_reranker()
        reranked = reranker.rerank_with_scores(query_text, documents, top_n=limit)

        # Check if reranking actually produced scores
        has_rerank = any(d.get("relevance_score") is not None for d in reranked)

        if has_rerank:
            # Blend Qdrant score with rerank score
            for d in reranked:
                qdrant_score = d.get("_qdrant_score", 0) * 100  # normalize to 0-100
                rerank_score = d.get("rerank_score", 0)
                d["final_score"] = reranker.blend_scores(qdrant_score, rerank_score, 0.5)
            reranked.sort(key=lambda d: d.get("final_score", 0), reverse=True)
        else:
            # Fallback: sort by Qdrant score
            reranked.sort(key=lambda d: d.get("_qdrant_score", 0), reverse=True)

        return reranked

    def get_relevant_context(self, query_vector: list[float], limit: int = 5) -> str:
        """
        Retrieve the most relevant context from all memory collections.
        Returns a formatted string suitable for agent prompts.

        Uses two-stage retrieval: Qdrant cosine similarity → Cohere rerank
        when both are available, falls back to Qdrant-only results.
        """
        sections = []

        # Search memory notes (no reranking — short text snippets)
        notes = self.search_vectors("memory_notes", query_vector, limit=limit)
        if notes:
            note_texts = []
            for n in notes:
                text = n.payload.get("text", "") if hasattr(n, "payload") else ""
                score = n.score if hasattr(n, "score") else 0
                if text:
                    note_texts.append(f"  [{score:.2f}] {text[:200]}")
            if note_texts:
                sections.append("📝 **Relevant Memories:**\n" + "\n".join(note_texts))

        # Search opportunity embeddings with Cohere rerank
        opps = self.search_vectors_reranked(
            "opportunity_embeddings",
            query_vector,
            query_text="retrieve matching opportunities from memory",
            limit=limit,
        )
        if opps:
            opp_texts = []
            for o in opps:
                title = o.get("title", "Untitled")
                company = o.get("company", "")
                final_score = o.get("final_score", o.get("_qdrant_score", 0))
                opp_texts.append(f"  [{final_score:.1f}] {title} @ {company}")
            if opp_texts:
                sections.append("💼 **Matching Opportunities:**\n" + "\n".join(opp_texts))

        return "\n\n".join(sections) if sections else "No relevant memory context found."
