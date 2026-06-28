"""
Rerank Service — uses Cohere's rerank API for two-stage retrieval.

After Qdrant retrieves top-K candidates by vector similarity (stage 1),
Cohere reranks them by semantic relevance to the query (stage 2).
The rerank scores are then blended with rule-based match scores.

Usage:
    reranker = RerankService()
    reranked = await reranker.rerank(
        query="AI internships in Ahmedabad",
        documents=[
            {"title": "ML Research Intern", "description": "..."},
            ...
        ],
        top_n=10,
    )
"""

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger("agentforge.rerank")


class RerankService:
    """Two-stage reranking using Cohere's rerank API."""

    def __init__(self):
        self.api_key = settings.cohere_api_key
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the Cohere client if an API key is configured."""
        if self.api_key:
            try:
                import cohere
                self.client = cohere.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to init Cohere client: %s", e)

    @property
    def available(self) -> bool:
        """Whether the Cohere client is available."""
        return self.client is not None

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
        model: str = "rerank-english-v3.0",
    ) -> list[dict[str, Any]]:
        """
        Rerank documents by semantic relevance to the query.

        Args:
            query: The search query or user goal.
            documents: List of dicts, each must have a 'title' key and
                       optionally 'description', 'company', 'skills_required'.
            top_n: Number of top results to return (default: len(documents)).
            model: Cohere rerank model name.

        Returns:
            List of documents with added 'relevance_score' (0-1),
            sorted by relevance descending.
        """
        if not self.client:
            logger.debug("Cohere client not available — returning original order with default scores")
            return self._fallback(documents)

        if not documents:
            return []

        # Build document strings for Cohere — combine title + description
        doc_strings = []
        for doc in documents:
            parts = [
                doc.get("title", ""),
                doc.get("company", ""),
                doc.get("description", ""),
            ]
            # Include skills if available
            skills = doc.get("skills_required", doc.get("skills", []))
            if skills:
                parts.append("Skills: " + ", ".join(skills) if isinstance(skills, list) else str(skills))
            doc_strings.append(" | ".join(p.strip() for p in parts if p.strip()))

        try:
            response = self.client.rerank(
                query=query,
                documents=doc_strings,
                model=model,
                top_n=top_n or len(documents),
            )

            # Map results back to original documents
            ranked = []
            for result in response.results:
                idx = result.index
                doc = dict(documents[idx])  # copy
                doc["relevance_score"] = result.relevance_score
                doc["rerank_index"] = idx
                ranked.append(doc)

            # Sort by relevance score descending
            ranked.sort(key=lambda d: d["relevance_score"], reverse=True)
            return ranked

        except Exception as e:
            logger.warning("Cohere rerank failed: %s — using fallback", e)
            return self._fallback(documents)

    async def rerank_with_scores(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
        model: str = "rerank-english-v3.0",
    ) -> list[dict[str, Any]]:
        """
        Rerank and include both the original match_score and the new
        relevance_score so callers can blend them.
        """
        reranked = await self.rerank(query, documents, top_n, model)

        # Normalize relevance scores to 0-100 range for blending
        if reranked and any(d.get("relevance_score") is not None for d in reranked):
            scores = [d.get("relevance_score", 0) for d in reranked]
            max_score = max(scores) if scores else 1
            for d in reranked:
                raw = d.get("relevance_score", 0)
                d["rerank_score"] = round((raw / max_score) * 100, 1) if max_score > 0 else 0

        return reranked

    def blend_scores(
        self,
        match_score: float,
        rerank_score: float | None,
        blend_weight: float = 0.4,
    ) -> float:
        """
        Blend the rule-based match score with the Cohere rerank score.

        Formula:
            final_score = (1 - blend_weight) * match_score + blend_weight * rerank_score

        If rerank_score is unavailable, returns match_score unchanged.
        """
        if rerank_score is None:
            return match_score
        return round((1 - blend_weight) * match_score + blend_weight * rerank_score, 1)

    def _fallback(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback when Cohere is unavailable — return docs with neutral scores."""
        result = []
        for i, doc in enumerate(documents):
            d = dict(doc)
            d["relevance_score"] = None
            d["rerank_score"] = None
            d["rerank_index"] = i
            result.append(d)
        return result


# Singleton for reuse across agents
_reranker: RerankService | None = None


def get_reranker() -> RerankService:
    """Get or create the singleton reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = RerankService()
    return _reranker
