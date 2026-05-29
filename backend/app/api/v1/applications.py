from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Application, ApplicationStage, Opportunity
from app.schemas.user import ApplicationCreate, ApplicationUpdate, ApplicationOut, ApplicationList, OpportunityOut

router = APIRouter()


@router.get("", response_model=ApplicationList)
async def list_applications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications for the current user."""
    query = (
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(desc(Application.created_at))
    )
    result = await db.execute(query)
    apps = result.scalars().all()

    items = []
    for app in apps:
        app_out = ApplicationOut.model_validate(app)
        if app.opportunity_id:
            opp_result = await db.execute(
                select(Opportunity).where(Opportunity.id == app.opportunity_id)
            )
            opp = opp_result.scalar_one_or_none()
            if opp:
                app_out.opportunity = OpportunityOut.model_validate(opp)
        items.append(app_out)

    return ApplicationList(items=items)


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(
    data: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application."""
    # Verify opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == data.opportunity_id)
    )
    if not opp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Opportunity not found")

    app = Application(
        user_id=user.id,
        opportunity_id=data.opportunity_id,
        notes=data.notes,
        applied_date=date.today(),
    )
    db.add(app)
    await db.flush()
    return app


@router.patch("/{id}", response_model=ApplicationOut)
async def update_application(
    id: str,
    data: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update application stage, notes, or next steps."""
    result = await db.execute(
        select(Application).where(Application.id == id, Application.user_id == user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(app, key, value)
    await db.flush()
    return app


@router.delete("/{id}", status_code=204)
async def delete_application(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an application."""
    result = await db.execute(
        select(Application).where(Application.id == id, Application.user_id == user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.delete(app)


@router.post("/{id}/tailor-resume")
async def tailor_resume(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the resume agent to tailor a resume for this application."""
    from app.agents.graph import run_resume_tailoring
    task_id = await run_resume_tailoring(str(user.id), id)
    return {"task_id": task_id}
