"""Internship Agent handlers — internship discovery and recommendations."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.opportunity_agent.service import OpportunityAgentService
from app.opportunity_agent.schemas import OpportunityResult

logger = logging.getLogger("agentforge.agents.internship.handlers")


async def discover_internships(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Discover internship opportunities matching the user's profile.

    Delegates to OpportunityAgentService for search, scoring, analysis, and feedback.
    """
    query = params.get("query", "internship")
    location = params.get("location")
    skills = params.get("skills", [])
    limit = params.get("limit", 20)

    if not query or not isinstance(query, str) or len(query.strip()) < 2:
        raise ValueError("Invalid query: must be a non-empty string with at least 2 characters")

    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 20

    try:
        service = OpportunityAgentService(db, user_id)
        result: OpportunityResult = await service.discover(
            query=query,
            location=location,
            skills=skills,
            limit=limit,
            source_filter="internship",
            opp_type="Internship",
        )

        return {
            "items": [i.model_dump() for i in result.items],
            "total": result.total,
            "agent": result.agent,
            "message": result.message,
            "summary": result.summary,
            "analysis": result.analysis.model_dump(),
            "feedback": result.feedback.model_dump(),
            "search_metadata": result.search_metadata,
        }
    except ValueError:
        raise
    except Exception as e:
        logger.error("Internship discovery failed for user %s: %s", user_id, str(e))
        raise


async def get_internship_recommendations(
    user_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """Get top-scored internship recommendations."""
    service = OpportunityAgentService(db, user_id)
    return await service.get_recommendations("Internship", limit)
