"""
Internship Agent — specialized in discovering, scoring, and tracking internships.

Integrates with:
- MemoryService for user preferences and history
- MatchService for scoring
- SearchAdapters for external sourcing
- Qdrant for semantic storage
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import (
    Opportunity,
    MatchScore,
)
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService
from app.services.match_service import MatchService
from app.search.adapters import SearchAdapter
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.agents.internship")


async def discover_internships(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Discover internship opportunities matching the user's profile.
    Searches external sources, scores matches, and stores in memory.
    """
    query = params.get("query", "internship")
    location = params.get("location")
    skills = params.get("skills", [])
    limit = params.get("limit", 20)

    # Load memory context for personalized search
    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    match_service = MatchService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    memory_context = await memory_service.get_user_context(user_id)

    # Merge params skills with profile skills
    all_skills = list(set(skills + profile_skills))

    # Search external sources
    search_adapter = SearchAdapter()
    try:
        raw_results = await search_adapter.search(
            query=query,
            location=location,
            skills=all_skills,
            limit=limit,
            source_filter="internship",
        )
    except Exception as e:
        logger.warning("External search failed, using demo data: %s", e)
        raw_results = _demo_internships(query, location)

    # Store results and score
    items = []
    opp_map: dict[str, Opportunity] = {}
    for r in raw_results[:limit]:
        opp = Opportunity(
            user_id=user_id,
            title=r.get("title", "Untitled Internship"),
            company=r.get("company", "Unknown"),
            company_logo=r.get("logo"),
            location=r.get("location"),
            remote=r.get("remote", False),
            type="Internship",
            description=r.get("description"),
            apply_url=r.get("apply_url"),
            skills_required=r.get("skills", all_skills),
            source=r.get("source", "internship_agent"),
            posted_date=r.get("posted_date"),
            deadline=r.get("deadline"),
        )
        db.add(opp)
        await db.flush()

        # Score match
        match_data = await match_service.calculate_match(user_id, opp)
        ms = MatchScore(
            opportunity_id=opp.id,
            user_id=user_id,
            overall_score=Decimal(str(match_data["overall"])),
            skill_score=Decimal(str(match_data["breakdown"]["skills"])),
            location_score=Decimal(str(match_data["breakdown"]["location"])),
            company_score=Decimal(str(match_data["breakdown"]["company"])),
            experience_score=Decimal(str(match_data["breakdown"]["experience"])),
            reasons=match_data["reasons"],
        )
        db.add(ms)

        # Store vector embedding in Qdrant
        await _store_opportunity_embedding(user_id, opp, match_data)

        opp_id = str(opp.id)
        opp_map[opp_id] = opp

        items.append(
            {
                "id": opp_id,
                "title": opp.title,
                "company": opp.company,
                "location": opp.location,
                "description": opp.description or "",
                "skills_required": opp.skills_required or [],
                "match_score": match_data["overall"],
                "reason": match_data["reasons"][0] if match_data["reasons"] else "",
            }
        )

    # ── Rerank with Cohere and blend scores ──
    if items and query:
        reranked = await match_service.rerank_and_blend(
            user_id, query, items, blend_weight=0.4
        )
        items = reranked

    # Update memory with search activity
    await memory_service.set_memory(
        user_id,
        "last_internship_search",
        {
            "query": query,
            "location": location,
            "results_count": len(items),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        weight=0.8,
    )

    await db.flush()

    return {
        "items": items,
        "total": len(items),
        "agent": "internship",
        "message": f"Found {len(items)} internship opportunities",
        "summary": f"Discovered {len(items)} internships matching your skills in {', '.join(all_skills[:3])}",
    }


async def get_internship_recommendations(
    user_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """Get top-scored internship recommendations from stored opportunities."""
    from sqlalchemy import select, desc

    result = await db.execute(
        select(Opportunity, MatchScore)
        .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
        .where(
            Opportunity.user_id == user_id,
            Opportunity.type == "Internship",
            Opportunity.is_active == True,
        )
        .order_by(desc(MatchScore.overall_score))
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "id": str(opp.id),
            "title": opp.title,
            "company": opp.company,
            "location": opp.location,
            "remote": opp.remote,
            "match_score": float(ms.overall_score),
            "reasons": ms.reasons or [],
            "deadline": opp.deadline.isoformat() if opp.deadline else None,
        }
        for opp, ms in rows
    ]


async def _store_opportunity_embedding(
    user_id: str, opp: Opportunity, match_data: dict
):
    """Store opportunity as a vector embedding for semantic retrieval."""
    try:
        agent_memory = AgentMemory(user_id)
        text = f"{opp.title} at {opp.company}. {opp.description or ''}"
        vector = await get_text_embedding(text)
        agent_memory.store_vector(
            collection="opportunity_embeddings",
            text=text,
            vector=vector,
            metadata={
                "title": opp.title,
                "company": opp.company,
                "type": "Internship",
                "match_score": match_data["overall"],
                "opportunity_id": str(opp.id),
            },
        )
    except Exception as e:
        logger.debug("Failed to store opportunity embedding: %s", e)


def _demo_internships(query: str, location: Optional[str]) -> list[dict]:
    """Demo internship data for development/testing."""
    return [
        {
            "title": "ML Research Intern",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "remote": True,
            "description": "Work on frontier AI safety research with world-class researchers.",
            "skills": ["Python", "PyTorch", "NLP"],
            "apply_url": "https://anthropic.com/careers",
            "source": "demo",
        },
        {
            "title": "Software Engineer Intern",
            "company": "Stripe",
            "location": "Remote" if not location else location,
            "remote": True,
            "description": "Build payment infrastructure used by millions of businesses.",
            "skills": ["TypeScript", "React", "Python"],
            "apply_url": "https://stripe.com/jobs",
            "source": "demo",
        },
        {
            "title": "Frontend Engineer Intern",
            "company": "Vercel",
            "location": "Remote",
            "remote": True,
            "description": "Help build the platform that powers the modern web.",
            "skills": ["React", "Next.js", "TypeScript"],
            "apply_url": "https://vercel.com/careers",
            "source": "demo",
        },
        {
            "title": "Data Science Intern",
            "company": "Netflix",
            "location": "Los Gatos, CA",
            "remote": False,
            "description": "Analyze streaming data to drive product decisions.",
            "skills": ["Python", "SQL", "Statistics"],
            "apply_url": "https://netflix.com/jobs",
            "source": "demo",
        },
    ]
