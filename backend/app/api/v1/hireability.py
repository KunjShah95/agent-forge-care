"""Hireability report — one HR-readable verdict from all public signals.

Combines GitHub activity, portfolio projects, Medium/blog writing, and an
optional resume evaluation into a transparent 0-100 score with evidence.

X/Twitter is intentionally excluded (no free API, login wall).
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.profile_enrichment import enrich_github_profile, enrich_portfolio
from app.services.social_signals import compute_hireability, fetch_blog_signals, fetch_medium_posts

logger = logging.getLogger("agentforge.api.hireability")

router = APIRouter()


class HireabilityRequest(BaseModel):
    github_url: str | None = None
    portfolio_url: str | None = None
    medium_handle: str | None = None
    blog_url: str | None = None
    resume_text: str | None = None
    position_type: str | None = None


@router.post("/report")
async def hireability_report(
    body: HireabilityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build a hireability report from the candidate's public profiles."""
    if not any([body.github_url, body.portfolio_url, body.medium_handle, body.blog_url, body.resume_text]):
        raise HTTPException(status_code=422, detail="Provide at least one source: github_url, portfolio_url, medium_handle, blog_url, or resume_text.")

    tasks: dict[str, asyncio.Task] = {}
    if body.github_url:
        tasks["github"] = asyncio.create_task(enrich_github_profile(body.github_url, db, str(user.id)))
    if body.portfolio_url:
        tasks["portfolio"] = asyncio.create_task(enrich_portfolio(body.portfolio_url, db, str(user.id)))
    if body.medium_handle:
        tasks["medium"] = asyncio.create_task(fetch_medium_posts(body.medium_handle))
    if body.blog_url:
        tasks["blog"] = asyncio.create_task(fetch_blog_signals(body.blog_url))

    results: dict = {}
    for key, task in tasks.items():
        try:
            results[key] = await task
        except Exception as e:
            logger.warning("Hireability source %s failed: %s", key, e)
            results[key] = {"error": str(e)[:200]}

    github_result = results.get("github")
    github_payload = {
        "github_profile": getattr(github_result, "github_profile", {}),
        "github_analysis": getattr(github_result, "github_analysis", {}),
        "social_links": getattr(github_result, "social_links", None).to_dict()
        if getattr(github_result, "social_links", None)
        else {},
        "github_oss": {},
        "github_contributions": {},
        "github_commit_analysis": {},
    }
    try:
        memory = MemoryService(db)
        for mem_key, out_key in [
            ("github_oss_contributions", "github_oss"),
            ("github_contributions", "github_contributions"),
            ("github_commit_analysis", "github_commit_analysis"),
        ]:
            val = await memory.get_memory(str(user.id), mem_key)
            if isinstance(val, dict):
                github_payload[out_key] = val
    except Exception as e:
        logger.debug("Hireability memory read failed: %s", e)

    portfolio_result = results.get("portfolio")
    portfolio_payload = getattr(portfolio_result, "portfolio_data", {}) or {}

    # Auto-discover Medium/blog from GitHub blog link when not explicitly given
    social = github_payload["social_links"]
    if not body.medium_handle and social.get("blog_url") and "medium.com/@" in social["blog_url"]:
        try:
            results["medium"] = await fetch_medium_posts(social["blog_url"])
        except Exception as e:
            logger.debug("Auto Medium fetch failed: %s", e)
    if not body.blog_url and social.get("blog_url") and "medium.com" not in social["blog_url"]:
        try:
            results["blog"] = await fetch_blog_signals(social["blog_url"])
        except Exception as e:
            logger.debug("Auto blog fetch failed: %s", e)

    resume_eval = None
    if body.resume_text:
        try:
            from app.hiring_agent.service import HiringAgentService

            svc = HiringAgentService(db, str(user.id))
            evaluated = await svc.evaluate_resume(body.resume_text, position_type=body.position_type)
            if evaluated:
                resume_eval = evaluated.model_dump() if hasattr(evaluated, "model_dump") else dict(evaluated)
        except Exception as e:
            logger.warning("Hireability resume eval failed: %s", e)

    report = compute_hireability(
        github=github_payload,
        portfolio=portfolio_payload,
        medium=results.get("medium", {}),
        blog=results.get("blog", {}),
        resume_eval=resume_eval,
    )

    try:
        await MemoryService(db).set_memory(
            str(user.id), "hireability_report", {**report, "inputs": body.model_dump()}, weight=0.9
        )
    except Exception as e:
        logger.debug("Hireability memory store failed: %s", e)

    return {
        **report,
        "signals": {
            "github": bool(github_payload.get("github_profile")),
            "portfolio": bool(portfolio_payload and "error" not in portfolio_payload),
            "medium": bool(results.get("medium", {}).get("posts")),
            "blog": bool(results.get("blog", {}).get("posts")),
            "resume": bool(resume_eval),
        },
    }
