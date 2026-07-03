"""
Integration layer between the opportunity agent service and the assistant agent.
Mirrors hiring_agent/assistant_integration.py pattern.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.opportunity_agent.service import OpportunityAgentService
from app.opportunity_agent.schemas import OpportunityResult, OpportunityScanResult, OpportunityFeedback

logger = logging.getLogger("agentforge.opportunity_agent.integration")


async def enrich_with_opportunity_agent(
    user_id: str,
    db: AsyncSession,
    query: Optional[str] = None,
    location: Optional[str] = None,
    skills: Optional[list[str]] = None,
    source_filter: str = "job",
    opp_type: str = "Full-time",
) -> OpportunityResult:
    """Run discovery and return structured results with feedback."""
    service = OpportunityAgentService(db, user_id)
    return await service.discover(
        query=query or "opportunities",
        location=location,
        skills=skills,
        source_filter=source_filter,
        opp_type=opp_type,
    )


async def enrich_with_opportunity_scan(
    user_id: str,
    db: AsyncSession,
    search_query: Optional[str] = None,
) -> OpportunityScanResult:
    """Run daily scan and return structured results with feedback."""
    service = OpportunityAgentService(db, user_id)
    return await service.run_scan(search_query=search_query)


async def get_detailed_feedback(
    user_id: str,
    db: AsyncSession,
    opportunity_id: str,
) -> dict:
    """Get detailed LLM-based fit analysis for a single opportunity."""
    service = OpportunityAgentService(db, user_id)
    return await service.analyze_opportunity_fit(opportunity_id)
