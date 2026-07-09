import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import MatchScore, Opportunity, User
from app.schemas.user import (
    OpportunityList,
    OpportunityOut,
    ScoredOpportunityList,
    ScoredOpportunityOut,
)

logger = logging.getLogger("agentforge.opportunities")

router = APIRouter()


def _extract_company_from_title(title: str) -> str:
    """Extract a company/organization name from a hackathon title."""
    m = re.search(r"\b(at|by|hosted by|presented by)\s+([A-Z][A-Za-z0-9\s&.]+)", title, re.I)
    if m:
        return m.group(2).strip()[:50]
    m = re.search(r"^([A-Z][A-Za-z0-9\s&.]+?)\s+Hackathon", title)
    if m:
        return m.group(1).strip()[:50]
    return "Hackathon"


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="The query to get suggestions for"),
):
    """Get autocomplete suggestions from Google."""
    from app.search.adapters import SearchAdapter

    adapter = SearchAdapter()
    suggestions = await adapter.get_suggestions(q)
    return {"suggestions": suggestions}


@router.get("", response_model=OpportunityList)
async def list_opportunities(
    type: str | None = Query(None),
    search: str | None = Query(None),
    remote: bool | None = Query(None),
    work_type: str | None = Query(None),
    city: str | None = Query(None),
    state: str | None = Query(None),
    country: str | None = Query(None),
    industry: str | None = Query(None),
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
    if work_type:
        query = query.where(Opportunity.work_type == work_type)
    if city:
        query = query.where(Opportunity.city.ilike(f"%{city}%"))
    if state:
        query = query.where(Opportunity.state.ilike(f"%{state}%"))
    if country:
        query = query.where(Opportunity.country.ilike(f"%{country}%"))
    if industry:
        query = query.where(Opportunity.industry.ilike(f"%{industry}%"))
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
            **OpportunityOut.model_validate(opp).model_dump(exclude={"match_score", "match_reasons"}),
            match_score=float(ms.overall_score),
            match_reasons=ms.reasons or [],
        )
        items.append(scored)

    return ScoredOpportunityList(items=items)


class RefreshRequest(BaseModel):
    query: str | None = None


@router.get("/hackathons")
async def search_upcoming_hackathons(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for upcoming hackathons from external sources."""
    from app.search.adapters import SearchAdapter

    try:
        adapter = SearchAdapter()
        results = await adapter.search(
            query="upcoming hackathons 2025 2026 register now",
            limit=15,
            source_filter="hackathon",
        )
        # If no real results, try research search
        if not results:
            results = await adapter.search_research(
                query="upcoming hackathons 2025 2026 tech competitions",
                limit=15,
            )

        # Normalize web search results to HackathonResult shape
        from_search = []
        for r in results or []:
            from_search.append(
                {
                    "title": r.get("title", "Untitled Hackathon"),
                    "company": r.get("company") or _extract_company_from_title(r.get("title", "")),
                    "location": r.get("location"),
                    # Map Tavily/Exa search fields
                    "description": r.get("description") or r.get("snippet", ""),
                    "apply_url": r.get("apply_url") or r.get("url", ""),
                    "deadline": None,
                    "source": r.get("source", "web"),
                    "skills_required": r.get("skills", []),
                }
            )

        # Also get opportunities already saved as Hackathon type
        hackathon_query = (
            select(Opportunity)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.type == "Hackathon",
                Opportunity.is_active.is_(True),
            )
            .order_by(desc(Opportunity.deadline))
            .limit(15)
        )
        hackathon_result = await db.execute(hackathon_query)
        saved_hackathons = hackathon_result.scalars().all()

        saved_data = []
        for h in saved_hackathons:
            saved_data.append(
                {
                    "id": str(h.id),
                    "title": h.title,
                    "company": h.company,
                    "location": h.location,
                    "city": h.city,
                    "state": h.state,
                    "country": h.country,
                    "description": h.description,
                    "apply_url": h.apply_url,
                    "deadline": h.deadline.isoformat() if h.deadline else None,
                    "source": h.source or "saved",
                    "skills_required": h.skills_required or [],
                }
            )

        return {
            "from_search": from_search,
            "saved": saved_data,
        }
    except Exception as e:
        logger.error("Failed to search hackathons: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search hackathons: {str(e)}",
        )


FILTER_RESULT_LIMIT = 100


@router.get("/filters")
async def get_filter_options(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available filter options (distinct cities, states, countries, industries)."""
    try:
        # Get distinct values for each filter field, limited to prevent unbounded results
        queries = {
            "cities": select(Opportunity.city)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.city.isnot(None),
                Opportunity.city != "",
            )
            .distinct()
            .order_by(Opportunity.city)
            .limit(FILTER_RESULT_LIMIT),
            "states": select(Opportunity.state)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.state.isnot(None),
                Opportunity.state != "",
            )
            .distinct()
            .order_by(Opportunity.state)
            .limit(FILTER_RESULT_LIMIT),
            "countries": select(Opportunity.country)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.country.isnot(None),
                Opportunity.country != "",
            )
            .distinct()
            .order_by(Opportunity.country)
            .limit(FILTER_RESULT_LIMIT),
            "industries": select(Opportunity.industry)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.industry.isnot(None),
                Opportunity.industry != "",
            )
            .distinct()
            .order_by(Opportunity.industry)
            .limit(FILTER_RESULT_LIMIT),
        }

        result = {}
        for key, q in queries.items():
            r = await db.execute(q)
            vals = [row[0] for row in r.all() if row[0]]
            result[key] = vals

        return result
    except Exception as e:
        logger.error("Failed to get filter options: %s", str(e))
        return {"cities": [], "states": [], "countries": [], "industries": []}


@router.get("/locations")
async def get_opportunity_locations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get opportunities grouped by location with approximate coordinates for map view."""
    from app.utils.coordinates import get_coordinates_async

    try:
        result = await db.execute(
            select(Opportunity).where(
                Opportunity.user_id == user.id,
                Opportunity.is_active.is_(True),
            )
        )
        opps = result.scalars().all()

        # Group by city+state+country and resolve coordinates (async with Nominatim)
        location_groups: dict[str, dict] = {}
        for opp in opps:
            key = f"{opp.city or ''}|{opp.state or ''}|{opp.country or ''}"
            if key in location_groups:
                location_groups[key]["count"] += 1
                location_groups[key]["opportunities"].append(opp)
            else:
                coords = await get_coordinates_async(opp.city, opp.state, opp.country)
                location_groups[key] = {
                    "city": opp.city,
                    "state": opp.state,
                    "country": opp.country,
                    "lat": coords[0] if coords else None,
                    "lng": coords[1] if coords else None,
                    "count": 1,
                    "avg_score": None,
                    "opportunities": [opp],
                }

        # Calculate avg scores per group
        locations = []
        for key, loc in location_groups.items():
            scores = []
            for opp in loc["opportunities"]:
                for ms in opp.match_scores or []:
                    if ms.overall_score:
                        scores.append(float(ms.overall_score))
            if scores:
                loc["avg_score"] = sum(scores) / len(scores)

            if loc["lat"] is not None and loc["lng"] is not None:
                locations.append(
                    {
                        "city": loc["city"],
                        "state": loc["state"],
                        "country": loc["country"],
                        "lat": loc["lat"],
                        "lng": loc["lng"],
                        "count": loc["count"],
                        "avg_score": loc["avg_score"],
                    }
                )

        return {"locations": locations}
    except Exception as e:
        logger.error("Failed to get opportunity locations: %s", str(e))
        return {"locations": []}


@router.get("/{id}", response_model=OpportunityOut)
async def get_opportunity(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single opportunity by ID."""
    if not id or not isinstance(id, str) or len(id.strip()) < 1:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(select(Opportunity).where(Opportunity.id == id, Opportunity.user_id == user.id))
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get opportunity for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve opportunity: {str(e)}")


class HackathonScanRequest(BaseModel):
    skills: list[str] | None = None
    alert_enabled: bool | None = None
    email_enabled: bool | None = None


async def _run_hackathon_scan(
    db: AsyncSession,
    user_id: str,
    skills: list[str] | None = None,
    persist_alert: bool | None = None,
    persist_email: bool | None = None,
    user_email: str | None = None,
) -> dict:
    """
    Core hackathon scan logic — reusable between the API endpoint and background task.

    Searches for upcoming hackathons, scores them against the user's profile skills,
    saves high-matches as opportunities, and creates in-app notifications.

    When user_email is set, notifications will also be sent via email (SendGrid).
    persist_alert and persist_email control whether to persist those preferences
    in the user's memory.

    Returns the same dict shape as the API endpoint (new_matches, total_found, message).
    """
    from app.search.adapters import SearchAdapter
    from app.services.memory_service import MemoryService
    from app.services.notification_service import create_notification
    from app.services.profile_service import ProfileService
    from app.utils.industry import detect_industry
    from app.utils.location import parse_location

    try:
        # ── Get user profile skills ──
        profile_service = ProfileService(db)
        profile = await profile_service.get_or_create_profile(user_id)
        profile_skills = await profile_service.get_skill_names(profile.id)
        user_skills = list(set((skills or []) + profile_skills))

        if not user_skills:
            return {
                "new_matches": [],
                "total_found": 0,
                "message": "No skills configured. Add skills to your profile to get matched.",
            }

        # ── Search for upcoming hackathons ──
        adapter = SearchAdapter()
        search_results = await adapter.search(
            query="upcoming hackathons 2025 2026 register now tech",
            limit=20,
            source_filter="hackathon",
        )
        if not search_results:
            search_results = await adapter.search_research(
                query="upcoming hackathons competitions coding 2025 2026",
                limit=20,
            )

        if not search_results:
            return {
                "new_matches": [],
                "total_found": 0,
                "message": "No hackathons found at this time. Try again later.",
            }

        # ── Get already-saved hackathon titles for dedup ──
        existing_result = await db.execute(
            select(Opportunity.title).where(
                Opportunity.user_id == user_id,
                Opportunity.type == "Hackathon",
            )
        )
        existing_titles = set(row[0].lower().strip() for row in existing_result.all() if row[0])

        # ── Score each hackathon against user skills ──
        new_matches = []
        for r in search_results:
            title = r.get("title", "")
            desc = r.get("description", "") or r.get("snippet", "")
            company = r.get("company") or _extract_company_from_title(title)

            # Dedup against saved hackathons
            title_lower = title.lower().strip()
            if title_lower in existing_titles:
                continue

            # Calculate skill match score
            combined_text = f"{title} {desc} {company}".lower()
            matched_skills = [s for s in user_skills if s.lower() in combined_text]
            skill_score = len(matched_skills) / max(len(user_skills), 1) * 100

            # Only keep matches above threshold (at least 1 skill match or 15%+)
            if len(matched_skills) < 1 and skill_score < 15:
                continue

            # Parse location
            loc_raw = r.get("location")
            parsed = parse_location(loc_raw)

            # Detect industry
            hackathon_industry = detect_industry(
                title=title,
                company=company,
                description=desc,
            )

            # Save as opportunity
            opp = Opportunity(
                user_id=user_id,
                title=title[:255],
                company=company[:255],
                location=loc_raw,
                city=parsed["city"],
                state=parsed["state"],
                country=parsed["country"],
                industry=hackathon_industry,
                type="Hackathon",
                description=desc[:500] if desc else None,
                apply_url=r.get("apply_url") or r.get("url", ""),
                skills_required=matched_skills,
                source=r.get("source", "hackathon_scan"),
            )
            db.add(opp)
            await db.flush()

            # Create notification (with email if user opted in)
            await create_notification(
                db,
                str(user_id),
                title=f"🎯 Hackathon match: {title[:60]}",
                body=(f"Found '{title}' by {company} — matches your skills: {', '.join(matched_skills[:3])}"),
                type="success",
                to_email=user_email if user_email else None,
            )

            new_matches.append(
                {
                    "id": str(opp.id),
                    "title": title,
                    "company": company,
                    "location": loc_raw,
                    "city": parsed["city"],
                    "state": parsed["state"],
                    "country": parsed["country"],
                    "description": desc[:200] if desc else None,
                    "apply_url": opp.apply_url,
                    "matched_skills": matched_skills,
                    "skill_score": round(skill_score, 1),
                }
            )

        await db.flush()

        # Persist preferences if provided
        memory = MemoryService(db)
        if persist_alert is not None:
            await memory.set_memory(
                str(user_id),
                "hackathon_alert_enabled",
                persist_alert,
                weight=0.9,
            )
        if persist_email is not None:
            await memory.set_memory(
                str(user_id),
                "hackathon_email_enabled",
                persist_email,
                weight=0.9,
            )
        # Update last_scan timestamp
        await memory.set_memory(
            str(user_id),
            "last_hackathon_scan",
            {
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "new_matches": len(new_matches),
                "total_searched": len(search_results),
            },
            weight=0.8,
        )

        return {
            "new_matches": new_matches,
            "total_found": len(new_matches),
            "message": (
                f"Found {len(new_matches)} new hackathon{'s' if len(new_matches) != 1 else ''} matching your skills!"
            ),
        }

    except Exception as e:
        logger.error("Hackathon scan failed for user %s: %s", user_id, str(e))
        raise


@router.post("/hackathons/scan")
async def scan_hackathon_alerts(
    body: HackathonScanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan for upcoming hackathons, match against user's skills, and create notifications.

    Delegates to _run_hackathon_scan for the shared logic.
    """
    try:
        result = await _run_hackathon_scan(
            db=db,
            user_id=str(user.id),
            skills=body.skills,
            persist_alert=body.alert_enabled,
            persist_email=body.email_enabled,
            user_email=user.email if body.email_enabled else None,
        )
        return result
    except Exception as e:
        logger.error("Hackathon scan failed for user %s: %s", user.id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Hackathon scan failed: {str(e)}",
        )


@router.post("/refresh", status_code=202)
async def refresh_opportunities(
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an agent search to refresh opportunities."""
    from app.agents.orchestrator.service import run_opportunity_scan

    try:
        query = body.query if body else None
        task_id = await run_opportunity_scan(str(user.id), query=query)
        return {"task_id": task_id}
    except Exception as e:
        logger.error("Failed to refresh opportunities for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to refresh opportunities: {str(e)}")
