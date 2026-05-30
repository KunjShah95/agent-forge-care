from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Opportunity, MatchScore
from app.schemas.user import (
    OpportunityOut,
    OpportunityList,
    ScoredOpportunityOut,
    ScoredOpportunityList,
)

router = APIRouter()


@router.get("", response_model=OpportunityList)
async def list_opportunities(
    type: str | None = Query(None),
    search: str | None = Query(None),
    remote: bool | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List opportunities with filtering and pagination."""
    query = select(Opportunity).where(Opportunity.user_id == user.id)

    if type:
        query = query.where(Opportunity.type == type)
    if remote is not None:
        query = query.where(Opportunity.remote == remote)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            Opportunity.title.ilike(search_term)
            | Opportunity.company.ilike(search_term)
            | Opportunity.description.ilike(search_term)
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(desc(Opportunity.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # Attach match scores (batched to avoid N+1)
    opportunity_list = []
    if items:
        opp_ids = [opp.id for opp in items]
        ms_result = await db.execute(
            select(MatchScore).where(
                MatchScore.opportunity_id.in_(opp_ids),
                MatchScore.user_id == user.id,
            )
        )
        ms_map = {ms.opportunity_id: ms for ms in ms_result.scalars().all()}
        for opp in items:
            ms = ms_map.get(opp.id)
            opp_out = OpportunityOut.model_validate(opp)
            if ms:
                opp_out.match_score = float(ms.overall_score)
                opp_out.match_reasons = ms.reasons or []
            opportunity_list.append(opp_out)

    return OpportunityList(items=opportunity_list, total=total, page=page)


@router.get("/matches", response_model=ScoredOpportunityList)
async def matched_opportunities(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all opportunities with match scores, sorted by score desc."""
    query = (
        select(Opportunity, MatchScore)
        .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
        .where(MatchScore.user_id == user.id)
        .order_by(desc(MatchScore.overall_score))
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for opp, ms in rows:
        scored = ScoredOpportunityOut(
            **OpportunityOut.model_validate(opp).model_dump(
                exclude={"match_score", "match_reasons"}
            ),
            match_score=float(ms.overall_score),
            match_reasons=ms.reasons or [],
        )
        items.append(scored)

    return ScoredOpportunityList(items=items)


@router.get("/{id}", response_model=OpportunityOut)
async def get_opportunity(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single opportunity by ID."""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == id, Opportunity.user_id == user.id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    ms_result = await db.execute(
        select(MatchScore).where(
            MatchScore.opportunity_id == opp.id,
            MatchScore.user_id == user.id,
        )
    )
    ms = ms_result.scalar_one_or_none()
    opp_out = OpportunityOut.model_validate(opp)
    if ms:
        opp_out.match_score = float(ms.overall_score)
        opp_out.match_reasons = ms.reasons or []
    return opp_out


@router.post("/refresh", status_code=202)
async def refresh_opportunities(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an agent search to refresh opportunities."""
    from app.agents.graph import run_opportunity_scan

    task_id = await run_opportunity_scan(str(user.id))
    return {"task_id": task_id}
