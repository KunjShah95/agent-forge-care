from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Opportunity, Application, ApplicationStage, MatchScore
from app.schemas.user import AnalyticsSummary, FunnelPoint, SkillDemand, ActivityPoint

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary metrics."""
    # Active matches (opportunities with score > 80)
    matches_result = await db.execute(
        select(func.count()).select_from(
            select(MatchScore)
            .where(
                MatchScore.user_id == user.id,
                MatchScore.overall_score >= 80,
            )
            .subquery()
        )
    )
    active_matches = matches_result.scalar() or 0

    # Applications count
    apps_result = await db.execute(
        select(func.count()).select_from(
            select(Application).where(Application.user_id == user.id).subquery()
        )
    )
    total_apps = apps_result.scalar() or 0

    # Interview rate (applications that reached interview)
    interviews_result = await db.execute(
        select(func.count()).select_from(
            select(Application)
            .where(
                Application.user_id == user.id,
                Application.stage.in_(
                    [
                        ApplicationStage.interview,
                        ApplicationStage.offer,
                    ]
                ),
            )
            .subquery()
        )
    )
    interview_count = interviews_result.scalar() or 0
    interview_rate = (interview_count / total_apps * 100) if total_apps > 0 else 0

    # Upcoming deadlines (next 7 days)
    from datetime import date, timedelta

    deadline_result = await db.execute(
        select(func.count()).select_from(
            select(Opportunity)
            .where(
                Opportunity.user_id == user.id,
                Opportunity.deadline.isnot(None),
                cast(Opportunity.deadline, Date) >= date.today(),
                cast(Opportunity.deadline, Date) <= date.today() + timedelta(days=7),
            )
            .subquery()
        )
    )
    deadlines = deadline_result.scalar() or 0

    return AnalyticsSummary(
        active_matches=active_matches,
        applications=total_apps,
        interview_rate=round(interview_rate, 1),
        deadlines=deadlines,
    )


@router.get("/funnel", response_model=list[FunnelPoint])
async def get_funnel(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get application funnel data."""
    stages = [
        ApplicationStage.saved,
        ApplicationStage.applied,
        ApplicationStage.oa,
        ApplicationStage.interview,
        ApplicationStage.offer,
    ]
    funnel = []
    for stage in stages:
        result = await db.execute(
            select(func.count()).select_from(
                select(Application)
                .where(
                    Application.user_id == user.id,
                    Application.stage == stage,
                )
                .subquery()
            )
        )
        count = result.scalar() or 0
        funnel.append(
            FunnelPoint(
                name=stage.value.capitalize(),
                value=count,
                rate=f"{count}/{len(stages)}",
            )
        )
    return funnel


@router.get("/skills-demand", response_model=list[SkillDemand])
async def get_skills_demand(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get skill demand index based on opportunities."""
    result = await db.execute(
        select(Opportunity.skills_required).where(
            Opportunity.user_id == user.id,
            Opportunity.is_active == True,
        )
    )
    skill_lists = result.scalars().all()

    # Count skill frequency
    from collections import Counter

    counter = Counter()
    for skills in skill_lists:
        for skill in skills:
            counter[skill] += 1

    max_count = max(counter.values()) if counter else 1
    return [
        SkillDemand(skill=skill, demand=round(count / max_count * 100, 1))
        for skill, count in counter.most_common(10)
    ]


@router.get("/activity", response_model=list[ActivityPoint])
async def get_activity(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get weekly activity data."""
    from datetime import date, timedelta

    today = date.today()
    activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_name = day.strftime("%a")

        apps_result = await db.execute(
            select(func.count()).select_from(
                select(Application)
                .where(
                    Application.user_id == user.id,
                    cast(Application.applied_date, Date) == day,
                )
                .subquery()
            )
        )
        apps_count = apps_result.scalar() or 0

        interview_result = await db.execute(
            select(func.count()).select_from(
                select(Application)
                .where(
                    Application.user_id == user.id,
                    Application.stage.in_(
                        [
                            ApplicationStage.interview,
                            ApplicationStage.offer,
                        ]
                    ),
                    cast(Application.updated_at, Date) == day,
                )
                .subquery()
            )
        )
        interview_count = interview_result.scalar() or 0

        activity.append(
            ActivityPoint(
                day=day_name,
                applications=apps_count,
                interviews=interview_count,
            )
        )
    return activity
