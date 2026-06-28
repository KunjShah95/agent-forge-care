import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.hiring_agent.service import HiringAgentService
from app.hiring_agent.schemas import ExtractedResume
from app.models.user import MemoryEntry

logger = logging.getLogger("agentforge.hiring_agent.integration")


async def _get_latest_resume_text(user_id: str, db: AsyncSession) -> str | None:
    """Fetch the most recent resume text from MemoryEntry."""
    result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user_id, MemoryEntry.key.like("resume_%"))
        .order_by(desc(MemoryEntry.created_at))
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return None
    return (entry.value or {}).get("text", "")


async def enrich_with_hiring_agent(
    user_id: str,
    db: AsyncSession,
    resume_text: str | None = None,
    target_role: str | None = None,
    target_company: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Run hiring agent enrichments and return structured results.

    Returns a dict with any of: ats, jd_match, cover_letter, resume_extracted.
    All fields are optional — only those that can be computed are present.
    """
    result: dict = {}
    service = HiringAgentService(db, user_id)

    if not resume_text:
        resume_text = await _get_latest_resume_text(user_id, db)
        if not resume_text:
            return result

    try:
        resume = await service._summarize_resume(resume_text)
        if not resume:
            return result
    except Exception:
        logger.exception("Hiring agent resume summarization failed")
        return result

    result["resume_extracted"] = resume
    ats_score = await service._compute_ats_score(resume)
    if ats_score:
        result["ats"] = ats_score

    if job_description:
        jd_match = await service._match_jd(resume, job_description)
        if jd_match:
            result["jd_match"] = jd_match

    if target_role and target_company:
        cover = await service._generate_cover_letter(
            resume, target_role, target_company, job_description or ""
        )
        if cover:
            result["cover_letter"] = cover

    return result
