"""
Job Agent — specialized in discovering full-time, new-grad, and startup job opportunities.

Integrates with:
- MemoryService for user career preferences
- MatchService for salary and company-size scoring
- SearchAdapters for external job boards
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
from app.utils.location import parse_location
from app.utils.industry import detect_industry
from app.utils.work_mode import infer_work_type

logger = logging.getLogger("agentforge.agents.job")


async def discover_jobs(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Discover job opportunities matching the user's profile career goals.
    Searches external sources, scores matches, and stores in memory.
    """
    query = params.get("query", "software engineer")
    location = params.get("location")
    skills = params.get("skills", [])
    limit = params.get("limit", 20)

    # Input validation
    if not query or not isinstance(query, str) or len(query.strip()) < 2:
        raise ValueError("Invalid query: must be a non-empty string with at least 2 characters")
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 20

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    match_service = MatchService(db)

    try:
        profile = await profile_service.get_or_create_profile(user_id)
        profile_skills = await profile_service.get_skill_names(profile.id)

        # Retrieve salary preferences from profile
        salary_min = profile.salary_min

        all_skills = list(set(skills + profile_skills))

        # Search external sources
        search_adapter = SearchAdapter()
        try:
            raw_results = await search_adapter.search(
                query=query,
                location=location,
                skills=all_skills,
                limit=limit,
                source_filter="job",
            )
            if not raw_results:
                logger.warning("External job search returned 0 results, using demo data")
                raw_results = _demo_jobs(query, location)
        except Exception as e:
            logger.warning("External job search failed, using demo data: %s", e)
            raw_results = _demo_jobs(query, location)

        # Skip jobs the user already has (cross-run dedup so refresh returns
        # unique openings instead of re-inserting the same ones).
        existing_result = await db.execute(
            select(Opportunity.title, Opportunity.company).where(
                Opportunity.user_id == user_id
            )
        )
        existing_keys = {
            (t.lower().strip(), (c or "").lower().strip())
            for t, c in existing_result.all()
            if t
        }

        items = []
        seen_keys = set()
        for r in raw_results[:limit]:
            # Filter by salary range if user specified
            job_salary_min = r.get("salary_min")
            if salary_min and job_salary_min and job_salary_min < salary_min * 0.7:
                continue

            title = r.get("title", "Untitled Position")
            company = r.get("company", "Unknown")
            key = (title.lower().strip(), (company or "").lower().strip())
            if key in seen_keys or key in existing_keys:
                continue
            seen_keys.add(key)

            # Parse location into city/state/country
            loc_raw = r.get("location")
            parsed = parse_location(loc_raw)

            industry = detect_industry(
                title=title,
                company=company,
                description=r.get("description", ""),
            )

            remote = r.get("remote", False)
            work_type = r.get("work_type") or infer_work_type(
                remote, title, r.get("description"), loc_raw
            )

            opp = Opportunity(
                user_id=user_id,
                title=title,
                company=company,
                company_logo=r.get("logo"),
                location=loc_raw,
                city=parsed["city"],
                state=parsed["state"],
                country=parsed["country"],
                industry=industry,
                remote=remote,
                work_type=work_type,
                type="Full-time",
                salary_min=job_salary_min,
                salary_max=r.get("salary_max"),
                description=r.get("description"),
                apply_url=r.get("apply_url"),
                company_size=r.get("company_size"),
                skills_required=r.get("skills", all_skills),
                source=r.get("source", "job_agent"),
                posted_date=r.get("posted_date"),
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

            await _store_job_embedding(user_id, opp, match_data)

            items.append(
                {
                    "id": str(opp.id),
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

        # Update memory
        await memory_service.set_memory(
            user_id,
            "last_job_search",
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
            "agent": "job",
            "message": f"Found {len(items)} job opportunities",
            "summary": f"Discovered {len(items)} jobs matching your skills in {', '.join(all_skills[:3])}",
        }

    except Exception as e:
        logger.error("Job discovery failed for user %s: %s", user_id, str(e))
        raise


async def get_job_recommendations(
    user_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """Get top-scored job recommendations."""
    from sqlalchemy import desc

    result = await db.execute(
        select(Opportunity, MatchScore)
        .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
        .where(
            Opportunity.user_id == user_id,
            Opportunity.type == "Full-time",
            Opportunity.is_active.is_(True),
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
        }
        for opp, ms in rows
    ]


async def _store_job_embedding(user_id: str, opp: Opportunity, match_data: dict):
    """Store job as vector embedding for semantic search."""
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
                "type": "Full-time",
                "match_score": match_data["overall"],
                "opportunity_id": str(opp.id),
            },
        )
    except Exception as e:
        logger.debug("Failed to store job embedding: %s", e)


def _demo_jobs(query: str, location: Optional[str]) -> list[dict]:
    """Demo job data for development/testing."""
    return [
        {
            "title": "Software Engineer, New Grad",
            "company": "Google",
            "location": "Mountain View, CA",
            "remote": False,
            "description": "Build products used by billions of users globally.",
            "skills": ["Python", "C++", "Algorithms"],
            "apply_url": "https://google.com/careers",
            "source": "demo",
            "salary_min": 120000,
            "salary_max": 180000,
            "company_size": "10000+",
        },
        {
            "title": "Product Engineer",
            "company": "Linear",
            "location": "New York, NY",
            "remote": True,
            "description": "Build the most loved issue tracking tool for modern teams.",
            "skills": ["React", "TypeScript", "Design"],
            "apply_url": "https://linear.app/jobs",
            "source": "demo",
            "salary_min": 140000,
            "salary_max": 200000,
            "company_size": "50-200",
        },
        {
            "title": "Founding Engineer",
            "company": "Helia Labs",
            "location": "San Francisco, CA",
            "remote": True,
            "description": "Early-stage AI startup building the future of developer tools.",
            "skills": ["Full-stack", "AI", "TypeScript"],
            "apply_url": "https://helia.dev/jobs",
            "source": "demo",
            "salary_min": 130000,
            "salary_max": 190000,
            "company_size": "2-10",
        },
        {
            "title": "ML Engineer",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "remote": False,
            "description": "Develop and deploy cutting-edge AI models.",
            "skills": ["Python", "PyTorch", "ML", "Distributed Systems"],
            "apply_url": "https://openai.com/careers",
            "source": "demo",
            "salary_min": 200000,
            "salary_max": 350000,
            "company_size": "500-1000",
        },
    ]
