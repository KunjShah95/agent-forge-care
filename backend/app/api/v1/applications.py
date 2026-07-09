import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import Application, Opportunity, User
from app.schemas.user import (
    ApplicationCreate,
    ApplicationList,
    ApplicationOut,
    ApplicationUpdate,
    OpportunityOut,
)

logger = logging.getLogger("agentforge.applications")

router = APIRouter()


@router.get("", response_model=ApplicationList)
async def list_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications for the current user."""
    try:
        count_result = await db.execute(
            select(func.count()).select_from(Application).where(Application.user_id == user.id)
        )
        total = count_result.scalar()

        offset = (page - 1) * limit
        query = (
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(desc(Application.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        apps = result.scalars().all()

        items = []
        for app in apps:
            app_out = ApplicationOut.model_validate(app)
            if app.opportunity_id:
                opp_result = await db.execute(select(Opportunity).where(Opportunity.id == app.opportunity_id))
                opp = opp_result.scalar_one_or_none()
                if opp:
                    app_out.opportunity = OpportunityOut.model_validate(opp)
            items.append(app_out)

        return ApplicationList(items=items, total=total, page=page)
    except Exception as e:
        logger.error("Failed to list applications for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(
    data: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application."""
    opp_id = str(data.opportunity_id) if data.opportunity_id else ""
    if not opp_id:
        raise HTTPException(status_code=422, detail="Opportunity ID must be a non-empty string")

    try:
        # Verify opportunity exists
        opp_result = await db.execute(select(Opportunity).where(Opportunity.id == data.opportunity_id))
        opp = opp_result.scalar_one_or_none()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        app = Application(
            user_id=user.id,
            opportunity_id=data.opportunity_id,
            notes=data.notes,
            applied_date=date.today(),
        )
        db.add(app)
        await db.flush()
        await db.refresh(app)

        # Build the response explicitly — returning the ORM object would make
        # Pydantic lazy-load `app.opportunity`, which raises MissingGreenlet in
        # async SQLAlchemy and 500s (rolling back the insert). Reuse the
        # opportunity we already fetched instead.
        app_out = ApplicationOut.model_validate(app)
        app_out.opportunity = OpportunityOut.model_validate(opp)
        return app_out
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create application for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create application: {str(e)}")


@router.patch("/{id}", response_model=ApplicationOut)
async def update_application(
    id: str,
    data: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update application stage, notes, or next steps."""
    if not id:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(select(Application).where(Application.id == id, Application.user_id == user.id))
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        payload = data.model_dump(exclude_unset=True)
        # Stage enum values are lowercase ("applied"); the UI sends capitalized
        # labels ("Applied", "OA"). Normalize so the enum column accepts them
        # instead of raising on flush.
        if payload.get("stage"):
            payload["stage"] = str(payload["stage"]).lower()
        for key, value in payload.items():
            setattr(app, key, value)
        await db.flush()
        await db.refresh(app)

        # Build response explicitly to avoid lazy-loading `app.opportunity`
        # during serialization (async MissingGreenlet → 500, rolls back update).
        app_out = ApplicationOut.model_validate(app)
        if app.opportunity_id:
            try:
                opp_result = await db.execute(select(Opportunity).where(Opportunity.id == app.opportunity_id))
                opp = opp_result.scalar_one_or_none()
                if opp:
                    app_out.opportunity = OpportunityOut.model_validate(opp)
            except Exception as e:
                logger.debug("Could not attach opportunity to application: %s", e)
        return app_out
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update application for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update application: {str(e)}")


@router.delete("/{id}", status_code=204)
async def delete_application(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an application."""
    if not id:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(select(Application).where(Application.id == id, Application.user_id == user.id))
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        await db.delete(app)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete application for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete application: {str(e)}")


@router.post("/{id}/tailor-resume")
async def tailor_resume(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the resume agent to tailor a resume for this application."""
    from app.agents.orchestrator.service import run_resume_tailoring

    task_id = await run_resume_tailoring(str(user.id), id)
    return {"task_id": task_id}
