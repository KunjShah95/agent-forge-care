import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.guidance_agent import GuidanceAgent
from app.agents.interview_agent import InterviewAgent
from app.agents.networking_agent import NetworkingAgent
from app.agents.resume_agent import ResumeAgent
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import AgentTask, AgentType, TaskStatus, User
from app.schemas.user import (
    CareerGuidanceRequest,
    CoverLetterRequest,
    InternshipDiscoverRequest,
    InterviewFeedbackRequest,
    InterviewPrepRequest,
    InterviewSessionCreate,
    InterviewSessionList,
    InterviewSessionOut,
    JobDiscoverRequest,
    NetworkingOutreachRequest,
    PlannerRunRequest,
    PlannerRunResponse,
    ResearchRequest,
    ResumeTailorRequest,
    TaskList,
    TaskOut,
)
from app.services.notification_service import create_notification

logger = logging.getLogger("agentforge.agents")

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

    # Input validation
    if not data.goal or not isinstance(data.goal, str) or len(data.goal.strip()) < 3:
        raise HTTPException(status_code=422, detail="Goal must be a non-empty string with at least 3 characters")

    try:
        task_id = await run_planner_agent(str(user.id), data.goal.strip())
        return PlannerRunResponse(task_id=task_id)
    except Exception as e:
        logger.error("Planner agent failed for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Planner agent failed: {str(e)}")


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


@router.delete("/tasks/clear", status_code=204)
async def clear_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all completed or failed agent tasks for the user."""
    from sqlalchemy import delete

    await db.execute(
        delete(AgentTask).where(
            AgentTask.user_id == user.id, AgentTask.status.in_([TaskStatus.completed, TaskStatus.failed])
        )
    )
    await db.commit()


@router.delete("/tasks/{id}", status_code=204)
async def delete_task(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agent task."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id))
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
    result = await db.execute(select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{id}/retry")
async def retry_task(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or completed agent task."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.running
    task.error = None
    task.started_at = datetime.now(UTC)
    task.completed_at = None
    await db.commit()

    try:
        if task.agent_type == AgentType.planner:
            from app.agents.graph import run_planner_agent

            goal = task.input.get("goal") or task.input.get("goal_text") or ""
            await run_planner_agent(str(user.id), goal)
            task.status = TaskStatus.completed
            task.completed_at = datetime.now(UTC)
            await db.commit()
        elif task.agent_type == AgentType.monitor:
            from app.agents.orchestrator.service import run_opportunity_scan

            await run_opportunity_scan(str(user.id))
            task.status = TaskStatus.completed
            task.completed_at = datetime.now(UTC)
            await db.commit()
        elif task.agent_type == AgentType.resume:
            from app.agents.orchestrator.service import run_resume_tailoring

            app_id = task.input.get("application_id")
            if app_id:
                await run_resume_tailoring(str(user.id), app_id)
            else:
                agent = ResumeAgent(db, str(user.id))
                res = await agent.run(task.input)
                task.status = TaskStatus.completed
                task.completed_at = datetime.now(UTC)
                await db.commit()
        else:
            from app.agents.orchestrator.service import dispatch_agent

            agent_str = task.agent_type.value if hasattr(task.agent_type, "value") else str(task.agent_type)
            res = await dispatch_agent(agent_str, str(user.id), task.input, db)
            task.output = res
            task.status = TaskStatus.completed
            task.completed_at = datetime.now(UTC)
            await db.commit()

        return {"status": "success", "message": f"Task {id} retried successfully"}
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        task.completed_at = datetime.now(UTC)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.post("/tasks/{id}/cancel")
async def cancel_task(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or queued agent task."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == id, AgentTask.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in (TaskStatus.queued, TaskStatus.running):
        task.status = TaskStatus.failed
        task.error = "Cancelled by user"
        task.completed_at = datetime.now(UTC)
        await db.commit()
        return {"status": "success", "message": f"Task {id} cancelled"}
    else:
        return {"status": "ignored", "message": f"Task {id} is not running"}


@router.post("/monitor/run", response_model=PlannerRunResponse, status_code=202)
async def run_monitor(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the opportunity monitor agent to scan for new openings."""
    from app.agents.orchestrator.service import run_opportunity_scan

    task_id = await run_opportunity_scan(str(user.id))
    return PlannerRunResponse(task_id=task_id)


@router.get("/monitor/alerts")
async def get_monitor_alerts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent alerts from the opportunity monitor."""
    try:
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
    except Exception as e:
        logger.error("Failed to get monitor alerts for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monitor alerts: {str(e)}")


@router.post("/interview-prep", status_code=200)
async def interview_prep(
    data: InterviewPrepRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(
            status_code=422, detail="Company name must be a non-empty string with at least 2 characters"
        )

    if not data.role or not isinstance(data.role, str) or len(data.role.strip()) < 2:
        raise HTTPException(status_code=422, detail="Role must be a non-empty string with at least 2 characters")

    if (
        not data.type
        or not isinstance(data.type, str)
        or data.type not in ["behavioral", "technical", "system", "mixed"]
    ):
        raise HTTPException(status_code=422, detail="Type must be one of: behavioral, technical, system, mixed")

    params = data.model_dump()
    # Map frontend's "role" to backend's "role_type"
    if "role" in params and "role_type" not in params:
        params["role_type"] = params.pop("role")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.interview,
            status=TaskStatus.running,
            input=params,
        )
        db.add(task)
        await db.commit()

        result = await InterviewAgent(db, str(user.id)).run(params)
        task.status = TaskStatus.completed
        task.output = result.output
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Interview prep ready",
            body=f"Questions prepared for {data.company} ({data.role})",
            type="success",
        )
        return result.output
    except Exception as e:
        logger.error("Interview prep failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
            task.status = TaskStatus.failed
            task.error = str(e)
            await db.commit()
        await create_notification(db, user.id, title="Interview prep failed", body=str(e)[:200], type="error")
        raise HTTPException(status_code=500, detail=f"Interview preparation failed: {str(e)}")


@router.post("/research", status_code=200)
async def research(
    data: ResearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.research_agent import conduct_research

    # Input validation
    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(
            status_code=422, detail="Company name must be a non-empty string with at least 2 characters"
        )

    params = data.model_dump()
    # Map frontend's "company" to backend's "query"
    if "company" in params and "query" not in params:
        params["query"] = params["company"]

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.research,
            status=TaskStatus.running,
            input=params,
        )
        db.add(task)
        await db.commit()

        result = await conduct_research(str(user.id), params, db)
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
        logger.error("Research failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
            task.status = TaskStatus.failed
            task.error = str(e)
            await db.commit()
        await create_notification(db, user.id, title="Research failed", body=str(e)[:200], type="error")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/cover-letter", status_code=200)
async def cover_letter(
    data: CoverLetterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(
            status_code=422, detail="Company name must be a non-empty string with at least 2 characters"
        )

    if not data.role or not isinstance(data.role, str) or len(data.role.strip()) < 2:
        raise HTTPException(status_code=422, detail="Role must be a non-empty string with at least 2 characters")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.resume,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

        result = await ResumeAgent(db, str(user.id)).run({"action": "cover_letter", **data.model_dump()})
        task.status = TaskStatus.completed
        task.output = result.output
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Cover letter ready",
            body=f"Cover letter for {data.company} ({data.role}) has been generated",
            type="success",
        )
        return result.output
    except Exception as e:
        logger.error("Cover letter generation failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
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
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")


@router.post("/resume-tailor", status_code=200)
async def resume_tailor(
    data: ResumeTailorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.role_type or not isinstance(data.role_type, str) or len(data.role_type.strip()) < 2:
        raise HTTPException(status_code=422, detail="Role type must be a non-empty string with at least 2 characters")

    # Note: skills are optional — the agent merges the user's profile skills, so
    # the UI can tailor with just a role/company. Don't reject an empty list.

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.resume,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

        result = await ResumeAgent(db, str(user.id)).run(data.model_dump())
        task.status = TaskStatus.completed
        task.output = result.output
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Resume tailored",
            body=f"Resume optimized for {data.target_company or 'target role'}",
            type="success",
        )
        return result.output
    except Exception as e:
        logger.error("Resume tailoring failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
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
        raise HTTPException(status_code=500, detail=f"Resume tailoring failed: {str(e)}")


@router.post("/career-guidance", status_code=200)
async def career_guidance(
    data: CareerGuidanceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.career_goal or not isinstance(data.career_goal, str) or len(data.career_goal.strip()) < 3:
        raise HTTPException(status_code=422, detail="Career goal must be a non-empty string with at least 3 characters")

    if not data.current_role or not isinstance(data.current_role, str) or len(data.current_role.strip()) < 2:
        raise HTTPException(
            status_code=422, detail="Current role must be a non-empty string with at least 2 characters"
        )

    if not data.target_role or not isinstance(data.target_role, str) or len(data.target_role.strip()) < 2:
        raise HTTPException(status_code=422, detail="Target role must be a non-empty string with at least 2 characters")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.research,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

        result = await GuidanceAgent(db, str(user.id)).run(data.model_dump())
        task.status = TaskStatus.completed
        task.output = result.output
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Career guidance ready",
            body="Your career guidance has been generated",
            type="success",
        )
        return result.output
    except Exception as e:
        logger.error("Career guidance failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
            task.status = TaskStatus.failed
            task.error = str(e)
            await db.commit()
        await create_notification(db, user.id, title="Career guidance failed", body=str(e)[:200], type="error")
        raise HTTPException(status_code=500, detail=f"Career guidance failed: {str(e)}")


@router.post("/networking-outreach", status_code=200)
async def networking_outreach(
    data: NetworkingOutreachRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.target_companies or not isinstance(data.target_companies, list) or len(data.target_companies) == 0:
        raise HTTPException(status_code=422, detail="Target companies must be a non-empty list")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.networking,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

        result = await NetworkingAgent(db, str(user.id)).run(data.model_dump())
        task.status = TaskStatus.completed
        task.output = result.output
        await db.commit()
        await create_notification(
            db,
            user.id,
            title="Outreach templates ready",
            body="Networking outreach templates have been generated",
            type="success",
        )
        return result.output
    except Exception as e:
        logger.error("Networking outreach failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
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
        raise HTTPException(status_code=500, detail=f"Networking outreach failed: {str(e)}")


@router.post("/internship-discover", status_code=200)
async def internship_discover(
    data: InternshipDiscoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.internship_agent import discover_internships

    # Input validation
    if not data.query or not isinstance(data.query, str) or len(data.query.strip()) < 2:
        raise HTTPException(status_code=422, detail="Query must be a non-empty string with at least 2 characters")

    if not data.location or not isinstance(data.location, str) or len(data.location.strip()) < 2:
        raise HTTPException(status_code=422, detail="Location must be a non-empty string with at least 2 characters")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.internship,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

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
        logger.error("Internship discovery failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
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
        raise HTTPException(status_code=500, detail=f"Internship discovery failed: {str(e)}")


@router.post("/job-discover", status_code=200)
async def job_discover(
    data: JobDiscoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.job_agent import discover_jobs

    # Input validation
    if not data.query or not isinstance(data.query, str) or len(data.query.strip()) < 2:
        raise HTTPException(status_code=422, detail="Query must be a non-empty string with at least 2 characters")

    if not data.location or not isinstance(data.location, str) or len(data.location.strip()) < 2:
        raise HTTPException(status_code=422, detail="Location must be a non-empty string with at least 2 characters")

    try:
        task = AgentTask(
            user_id=user.id,
            agent_type=AgentType.job,
            status=TaskStatus.running,
            input=data.model_dump(),
        )
        db.add(task)
        await db.commit()

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
        logger.error("Job discovery failed for user %s: %s", user.id, str(e))
        # Clean up task if it was created
        if "task" in locals():
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
        raise HTTPException(status_code=500, detail=f"Job discovery failed: {str(e)}")


@router.post("/opportunity-fit-analysis", status_code=200)
async def opportunity_fit_analysis(
    opportunity_id: str = Query(..., description="Opportunity ID to analyze"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed LLM-based fit analysis for a specific opportunity."""
    from app.opportunity_agent.assistant_integration import get_detailed_feedback

    try:
        result = await get_detailed_feedback(str(user.id), db, opportunity_id)
        return result
    except Exception as e:
        logger.error("Opportunity fit analysis failed for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Fit analysis failed: {str(e)}")


# ─── Interview Sessions ─────────────────────────────────────


@router.get("/interview-sessions", response_model=InterviewSessionList)
async def list_interview_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import MemoryEntry

    try:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key == "interview_sessions",
            )
        )
        entry = result.scalar_one_or_none()
        sessions = entry.value if entry and entry.value else []
        return InterviewSessionList(items=[InterviewSessionOut(**s) for s in sessions])
    except Exception as e:
        logger.error("Failed to list interview sessions for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interview sessions: {str(e)}")


@router.post("/interview-sessions", status_code=201)
async def create_interview_session(
    data: InterviewSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    from app.models.user import MemoryEntry

    # Input validation
    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(status_code=422, detail="Company must be a non-empty string with at least 2 characters")

    if (
        not data.type
        or not isinstance(data.type, str)
        or data.type not in ["behavioral", "technical", "system", "mixed"]
    ):
        raise HTTPException(status_code=422, detail="Type must be one of: behavioral, technical, system, mixed")

    if not isinstance(data.score, (int, float)) or data.score < 0 or data.score > 100:
        raise HTTPException(status_code=422, detail="Score must be a number between 0 and 100")

    if not isinstance(data.duration, (int, float)) or data.duration < 0:
        raise HTTPException(status_code=422, detail="Duration must be a non-negative number")

    try:
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
            "date": datetime.now(UTC).strftime("%b %d"),
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
    except Exception as e:
        logger.error("Failed to create interview session for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create interview session: {str(e)}")


# ─── Interview Feedback ─────────────────────────────────────


@router.post("/interview-feedback", status_code=200)
async def interview_feedback(
    data: InterviewFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not data.question or not isinstance(data.question, str) or len(data.question.strip()) < 3:
        raise HTTPException(status_code=422, detail="Question must be a non-empty string with at least 3 characters")

    if not data.answer or not isinstance(data.answer, str) or len(data.answer.strip()) < 3:
        raise HTTPException(status_code=422, detail="Answer must be a non-empty string with at least 3 characters")

    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(status_code=422, detail="Company must be a non-empty string with at least 2 characters")

    if not data.role or not isinstance(data.role, str) or len(data.role.strip()) < 2:
        raise HTTPException(status_code=422, detail="Role must be a non-empty string with at least 2 characters")

    try:
        result = await InterviewAgent(db, str(user.id)).run({"action": "review", **data.model_dump()})
        return result.output
    except Exception as e:
        logger.error("Interview feedback failed for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Interview feedback failed: {str(e)}")
