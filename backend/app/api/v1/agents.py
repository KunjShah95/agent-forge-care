from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.dependencies import get_current_user, limiter
from app.models.user import User, AgentTask, AgentType, TaskStatus
from app.schemas.user import (
    PlannerRunRequest,
    TaskOut,
    TaskList,
    PlannerRunResponse,
    InterviewPrepRequest,
    ResearchRequest,
    CoverLetterRequest,
    ResumeTailorRequest,
)

router = APIRouter()


@router.post("/planner/run", response_model=PlannerRunResponse, status_code=202)
@limiter.limit("10/minute")
async def run_planner(
    request: Request,
    data: PlannerRunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a goal to the planner agent for execution."""
    from app.agents.graph import run_planner_agent

    task_id = await run_planner_agent(str(user.id), data.goal)
    return PlannerRunResponse(task_id=task_id)


@router.get("/planner/status")
async def get_planner_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of the planner and recent activity."""
    result = await db.execute(
        select(func.count()).select_from(
            select(AgentTask)
            .where(
                AgentTask.user_id == user.id,
                AgentTask.agent_type == AgentType.planner,
            )
            .subquery()
        )
    )
    total = result.scalar() or 0

    # Latest planner task
    latest_result = await db.execute(
        select(AgentTask)
        .where(AgentTask.user_id == user.id, AgentTask.agent_type == AgentType.planner)
        .order_by(desc(AgentTask.created_at))
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    return {
        "total_goals": total,
        "latest_goal": latest.goal_id if latest else None,
        "latest_status": latest.status.value if latest else None,
        "is_running": latest is not None and latest.status == TaskStatus.running,
    }


@router.get("/tasks", response_model=TaskList)
async def list_tasks(
    status: str | None = Query(None),
    agent_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agent tasks with optional filtering."""
    query = select(AgentTask).where(AgentTask.user_id == user.id)

    if status:
        query = query.where(AgentTask.status == TaskStatus(status))
    if agent_type:
        query = query.where(AgentTask.agent_type == AgentType(agent_type))

    query = query.order_by(desc(AgentTask.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskList(items=[TaskOut.model_validate(t) for t in tasks])


@router.get("/tasks/{id}", response_model=TaskOut)
async def get_task(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single agent task with full details."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/monitor/run", response_model=PlannerRunResponse, status_code=202)
@limiter.limit("10/minute")
async def run_monitor(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the opportunity monitor agent to scan for new openings."""
    from app.agents.graph import run_opportunity_scan

    task_id = await run_opportunity_scan(str(user.id))
    return PlannerRunResponse(task_id=task_id)


@router.get("/monitor/alerts")
async def get_monitor_alerts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent alerts from the opportunity monitor."""
    from app.models.user import AgentType

    result = await db.execute(
        select(AgentTask)
        .where(
            AgentTask.user_id == user.id,
            AgentTask.agent_type == AgentType.monitor,
        )
        .order_by(desc(AgentTask.created_at))
        .limit(10)
    )
    tasks = result.scalars().all()
    alerts = []
    for task in tasks:
        if task.output and task.output.get("alerts"):
            alerts.extend(task.output["alerts"])
    return {"items": alerts[:20]}


@router.post("/interview-prep", status_code=200)
@limiter.limit("10/minute")
async def interview_prep(
    request: Request,
    data: InterviewPrepRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import prepare_interview

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.interview,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await prepare_interview(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research", status_code=200)
@limiter.limit("10/minute")
async def research(
    request: Request,
    data: ResearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.research_agent import conduct_research

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.research,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await conduct_research(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cover-letter", status_code=200)
@limiter.limit("10/minute")
async def cover_letter(
    request: Request,
    data: CoverLetterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import generate_cover_letter

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.resume,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await generate_cover_letter(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-tailor", status_code=200)
@limiter.limit("10/minute")
async def resume_tailor(
    request: Request,
    data: ResumeTailorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import tailor_resume

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.resume,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await tailor_resume(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))
