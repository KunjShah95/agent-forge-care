"""Career insights — differentiators vs Teal/Huntr/Simplify.

- salary-insights: median/min/max pay bands from saved opportunities
- skill-gap: profile skills vs opportunity requirements + learning focus
- upcoming-deadlines: unified deadline feed (opportunities + applications)
"""

import logging
from datetime import date
from statistics import median

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import Application, MatchScore, Opportunity, User
from app.schemas.user import OpportunityOut

logger = logging.getLogger("agentforge.insights")

router = APIRouter()


@router.get("/salary-insights")
async def salary_insights(
    title: str | None = Query(None, description="Role title filter, e.g. 'frontend'"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate pay bands from the user's saved opportunities (offer-coach input)."""
    q = select(Opportunity).where(Opportunity.user_id == user.id)
    if title:
        term = f"%{title.replace('%', '').replace('_', '')}%"
        q = q.where(Opportunity.title.ilike(term))
    result = await db.execute(q.limit(500))
    opps = result.scalars().all()
    bands = [(o.salary_min, o.salary_max) for o in opps if o.salary_min or o.salary_max]
    if not bands:
        return {"count": 0, "message": "No salary data yet — save roles with pay ranges."}
    mins = [b[0] for b in bands if b[0]]
    maxs = [b[1] for b in bands if b[1]]
    mids = [((a or 0) + (b or a or 0)) / 2 for a, b in bands if a or b]
    return {
        "count": len(bands),
        "min": min(mins) if mins else None,
        "median_mid": round(median(mids)) if mids else None,
        "max": max(maxs) if maxs else None,
        "currency": "USD",
        "negotiation_tip": "Ask 10-15% above the median mid for your competing offer.",
    }


@router.get("/skill-gap/{opportunity_id}")
async def skill_gap(
    opportunity_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare profile skills vs a role's required skills. Returns gaps + strengths."""
    import uuid as _uuid

    try:
        oid = _uuid.UUID(str(opportunity_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=422, detail="opportunity_id must be a valid UUID")

    from app.models.user import Profile, ProfileSkill, Skill

    opp = (await db.execute(select(Opportunity).where(Opportunity.id == oid, Opportunity.user_id == user.id))).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    prof = (await db.execute(select(Profile).where(Profile.user_id == user.id))).scalar_one_or_none()
    mine: set[str] = set()
    if prof:
        rows = await db.execute(
            select(Skill.name).join(ProfileSkill, ProfileSkill.skill_id == Skill.id).where(ProfileSkill.profile_id == prof.id)
        )
        mine = {r[0].lower() for r in rows.all() if r[0]}

    required = [s for s in (opp.skills_required or []) if s]
    req_lower = {s.lower(): s for s in required}
    matched = sorted([req_lower[k] for k in req_lower if k in mine])
    missing = sorted([req_lower[k] for k in req_lower if k not in mine])

    ms = (await db.execute(select(MatchScore).where(MatchScore.opportunity_id == opp.id, MatchScore.user_id == user.id))).scalar_one_or_none()

    return {
        "opportunity": OpportunityOut.model_validate(opp).model_dump(include={"id", "title", "company"}),
        "matched": matched,
        "missing": missing,
        "coverage_pct": round(len(matched) / max(len(required), 1) * 100, 1),
        "match_score": float(ms.overall_score) if ms and ms.overall_score else None,
        "match_reasons": (ms.reasons or []) if ms else [],
        "learn_next": missing[:3],
    }


@router.get("/upcoming-deadlines")
async def upcoming_deadlines(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified deadline feed from opportunities + application next-steps."""
    today = date.today()
    opps = (
        await db.execute(
            select(Opportunity)
            .where(Opportunity.user_id == user.id, Opportunity.is_active.is_(True), Opportunity.deadline.isnot(None))
            .order_by(Opportunity.deadline)
            .limit(limit)
        )
    ).scalars().all()
    apps = (
        await db.execute(
            select(Application)
            .where(Application.user_id == user.id, Application.next_date.isnot(None))
            .order_by(Application.next_date)
            .limit(limit)
        )
    ).scalars().all()

    items = [
        {"kind": "opportunity", "id": str(o.id), "title": o.title, "company": o.company, "date": o.deadline.isoformat(), "overdue": o.deadline < today}
        for o in opps
    ]
    items += [
        {"kind": "application", "id": str(a.id), "title": a.next_step or "Follow-up", "company": "", "date": a.next_date.isoformat(), "overdue": a.next_date < today}
        for a in apps
    ]
    items.sort(key=lambda x: x["date"])
    sliced = items[:limit]
    return {"items": sliced, "total": len(sliced), "today": today.isoformat()}
