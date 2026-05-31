from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, AgentTask, AgentType, TaskStatus
from app.services.notification_service import create_notification
from app.schemas.user import (
    PlannerRunRequest,
    TaskOut,
    TaskList,
    PlannerRunResponse,
    InterviewPrepRequest,
    ResearchRequest,
    CoverLetterRequest,
    ResumeTailorRequest,
    CareerGuidanceRequest,
    NetworkingOutreachRequest,
    InterviewFeedbackRequest,
    InterviewSessionOut,
    InterviewSessionList,
    InterviewSessionCreate,
    InternshipDiscoverRequest,
    JobDiscoverRequest,
)

router = APIRouter()


@router.get("/health")
async def agent_health():
    """Check if the agent system is healthy and report available agents."""
    from app.agents.graph import get_planner_graph

    try:
        graph = get_planner_graph()
        return {
            "status": "healthy",
            "agent_count": 8,
            "agents": [
                "planner",
                "internship",
                "job",
                "research",
                "resume",
                "interview",
                "networking",
                "monitor",
            ],
            "graph_compiled": graph is not None,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post("/planner/run", response_model=PlannerRunResponse, status_code=202)
async def run_planner(
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


@router.delete("/tasks/{id}", status_code=204)
async def delete_task(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agent task."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)


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
async def run_monitor(
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
async def interview_prep(
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
        await create_notification(
            db,
            user.id,
            title="Interview prep ready",
            body=f"Questions prepared for {data.company} ({data.role})",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db, user.id, title="Interview prep failed", body=str(e)[:200], type="error"
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research", status_code=200)
async def research(
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
        await create_notification(
            db,
            user.id,
            title="Research complete",
            body=f"Company research for {data.company} is ready",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db, user.id, title="Research failed", body=str(e)[:200], type="error"
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cover-letter", status_code=200)
async def cover_letter(
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
        await create_notification(
            db,
            user.id,
            title="Cover letter ready",
            body=f"Cover letter for {data.company} ({data.role}) has been generated",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Cover letter generation failed",
            body=str(e)[:200],
            type="error",
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-tailor", status_code=200)
async def resume_tailor(
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
        await create_notification(
            db,
            user.id,
            title="Resume tailored",
            body=f"Resume optimized for {data.target_company or 'target role'}",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Resume tailoring failed",
            body=str(e)[:200],
            type="error",
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/career-guidance", status_code=200)
async def career_guidance(
    data: CareerGuidanceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import get_career_guidance

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.research,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await get_career_guidance(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Career guidance ready",
            body="Your career guidance has been generated",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db, user.id, title="Career guidance failed", body=str(e)[:200], type="error"
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/networking-outreach", status_code=200)
async def networking_outreach(
    data: NetworkingOutreachRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import generate_outreach

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.networking,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await generate_outreach(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Outreach templates ready",
            body="Networking outreach templates have been generated",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Outreach generation failed",
            body=str(e)[:200],
            type="error",
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/internship-discover", status_code=200)
async def internship_discover(
    data: InternshipDiscoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.internship_agent import discover_internships

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.internship,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await discover_internships(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        await create_notification(
            db,
            str(user.id),
            title="Internship discovery complete",
            body=f"Found {len(result.get('items', []))} internship matches",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db,
            str(user.id),
            title="Internship discovery failed",
            body=str(e)[:200],
            type="error",
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job-discover", status_code=200)
async def job_discover(
    data: JobDiscoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.job_agent import discover_jobs

    task = AgentTask(
        user_id=user.id,
        agent_type=AgentType.job,
        status=TaskStatus.running,
        input=data.model_dump(),
    )
    db.add(task)
    await db.commit()
    try:
        result = await discover_jobs(str(user.id), data.model_dump(), db)
        task.status = TaskStatus.completed
        task.output = result
        await db.commit()
        await create_notification(
            db,
            str(user.id),
            title="Job discovery complete",
            body=f"Found {len(result.get('items', []))} job matches",
            type="success",
        )
        return result
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        await db.commit()
        await create_notification(
            db,
            str(user.id),
            title="Job discovery failed",
            body=str(e)[:200],
            type="error",
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ─── Interview Sessions ─────────────────────────────────────


@router.get("/interview-sessions", response_model=InterviewSessionList)
async def list_interview_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import MemoryEntry

    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key == "interview_sessions",
        )
    )
    entry = result.scalar_one_or_none()
    sessions = entry.value if entry and entry.value else []
    return InterviewSessionList(items=[InterviewSessionOut(**s) for s in sessions])


@router.post("/interview-sessions", status_code=201)
async def create_interview_session(
    data: InterviewSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import MemoryEntry
    import uuid

    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key == "interview_sessions",
        )
    )
    entry = result.scalar_one_or_none()
    session = {
        "id": str(uuid.uuid4())[:8],
        "company": data.company,
        "type": data.type,
        "date": datetime.now(timezone.utc).strftime("%b %d"),
        "score": data.score,
        "duration": data.duration,
    }
    if entry:
        sessions = entry.value or []
        sessions.append(session)
        entry.value = sessions
    else:
        entry = MemoryEntry(
            user_id=user.id,
            key="interview_sessions",
            value=[session],
        )
        db.add(entry)
    await db.flush()
    return InterviewSessionOut(**session)


# ─── Interview Feedback ─────────────────────────────────────


@router.post("/interview-feedback", status_code=200)
async def interview_feedback(
    data: InterviewFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.assistant_agent import review_interview_answer

    result = await review_interview_answer(str(user.id), data.model_dump(), db)
    return result
