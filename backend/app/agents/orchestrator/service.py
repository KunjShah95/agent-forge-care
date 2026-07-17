import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.guidance_agent import GuidanceAgent
from app.agents.internship_agent import InternshipAgent
from app.agents.interview_agent import InterviewAgent
from app.agents.job_agent import JobAgent
from app.agents.monitor_agent import MonitorAgent
from app.agents.networking_agent import NetworkingAgent
from app.agents.orchestrator.schemas import TaskDef
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.research_agent import ResearchAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.schemas import AgentResult, AgentStatus
from app.database import async_session_factory
from app.models.user import AgentTask as AgentTaskModel
from app.models.user import Application, Opportunity, PlannerGoal, TaskStatus
from app.services.notification_service import create_notification

logger = logging.getLogger("agentforge.orchestrator")

MAX_RETRIES = 2
RETRY_DELAY_SECS = 1.0
AGENT_TIMEOUT_SECS = 120


def _gen_id() -> str:
    return str(uuid.uuid4())


# ── Single source of truth for agent registries ─────────────

AGENT_REGISTRY: dict[str, Any] = {
    "resume": lambda db, uid: ResumeAgent(db, uid),
    "interview": lambda db, uid: InterviewAgent(db, uid),
    "networking": lambda db, uid: NetworkingAgent(db, uid),
    "monitor": lambda db, uid: MonitorAgent(db, uid),
    "guidance": lambda db, uid: GuidanceAgent(db, uid),
    "internship": lambda db, uid: InternshipAgent(db, uid),
    "job": lambda db, uid: JobAgent(db, uid),
    "research": lambda db, uid: ResearchAgent(db, uid),
    "discovery": lambda db, uid: DiscoveryAgent(db, uid),
}


# ── Retry / Timeout Helpers ─────────────────────────────────


async def _run_with_retry(coro_factory: Callable[[], Any], label: str) -> Any:
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(coro_factory(), timeout=AGENT_TIMEOUT_SECS)
        except TimeoutError as e:
            last_exc = e
            logger.warning(
                "%s timed out (%ds) attempt %d/%d",
                label,
                AGENT_TIMEOUT_SECS,
                attempt + 1,
                MAX_RETRIES + 1,
            )
        except Exception as e:
            last_exc = e
            logger.warning(
                "%s failed (attempt %d/%d): %s",
                label,
                attempt + 1,
                MAX_RETRIES + 1,
                e,
            )
        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY_SECS * (2**attempt))
    raise last_exc


# ── Main Orchestrator Agent ─────────────────────────────────
# Delegates to the LangGraph StateGraph in graph_engine.py.
# This class is kept for backward compatibility — new code should call
# ``run_planner_graph(db, user_id, goal)`` directly.


class OrchestratorAgent(BaseAgent):
    agent_type = "orchestrator"

    def __init__(self, db: AsyncSession, user_id: str):
        super().__init__(db, user_id)
        self.run_id: str = str(uuid.uuid4())
        self.results: dict[str, AgentResult] = {}

    async def execute(self, params: dict) -> dict:
        from app.agents.graph_engine import run_planner_graph

        goal = params.get("goal", "")
        if not goal:
            return {"error": "No goal provided", "run_id": self.run_id}

        # Delegate to the LangGraph StateGraph engine
        output = await run_planner_graph(self.db, self.user_id, goal)

        # Reconstruct AgentResult objects from graph output for legacy callers
        results = output.get("results", {})
        detail = output.get("detail", {})
        reflection_scores = output.get("reflection_scores", {})
        trace_url = output.get("trace_url")

        for agent_type, res in results.items():
            status = (
                AgentStatus.COMPLETED if res.get("status") == AgentStatus.COMPLETED else AgentStatus.FAILED
            )
            self.results[agent_type] = AgentResult(
                agent_type=agent_type,
                status=status,
                output=detail.get(agent_type),
                error=res.get("message") if status == AgentStatus.FAILED else None,
                duration_ms=res.get("duration_ms"),
            )

        return {
            "run_id": output.get("run_id", self.run_id),
            "goal": goal,
            "status": "completed",
            "results": results,
            "reflection_scores": reflection_scores,
            "detail": detail,
            "trace_url": trace_url,
        }


# ── Top-Level Entry Points ──────────────────────────────────
# These shared functions are the canonical dispatch entry points used by
# API routes (agents.py, opportunities.py, applications.py).
# graph.py imports these rather than duplicating them.


async def run_opportunity_scan(user_id: str, query: str | None = None) -> str:
    """Run an opportunity scan via the MonitorAgent directly."""
    from app.agents.monitor_agent import MonitorAgent

    task_id = _gen_id()
    params = {"action": "scan"}
    if query:
        params["search_query"] = query

    async with async_session_factory() as db:
        task = AgentTaskModel(
            id=task_id,
            user_id=user_id,
            agent_type="monitor",
            input=params,
            status=TaskStatus.running,
            started_at=datetime.now(UTC),
        )
        db.add(task)
        await db.flush()

        try:
            agent = MonitorAgent(db, user_id)
            result = await agent.run(params)
            task.status = TaskStatus.completed
            task.output = result.output or {}
            task.completed_at = datetime.now(UTC)
            await create_notification(
                db,
                user_id,
                title="Opportunity scan complete",
                body="New opportunities may be available.",
                type="info",
            )
        except Exception as e:
            task.status = TaskStatus.failed
            task.error = str(e)
            task.completed_at = datetime.now(UTC)
            await db.rollback()
            return task_id
        await db.commit()
    return task_id


async def run_resume_tailoring(user_id: str, application_id: str) -> str:
    """Run resume tailoring for a specific application via ResumeAgent directly."""
    from app.agents.resume_agent import ResumeAgent

    task_id = _gen_id()
    async with async_session_factory() as db:
        result = await db.execute(select(Application).where(Application.id == application_id))
        app = result.scalar_one_or_none()

        task = AgentTaskModel(
            id=task_id,
            user_id=user_id,
            agent_type="resume",
            input={"application_id": application_id},
            status=TaskStatus.running,
            started_at=datetime.now(UTC),
        )

        if app:
            opp_result = await db.execute(select(Opportunity).where(Opportunity.id == app.opportunity_id))
            opp = opp_result.scalar_one_or_none()
            agent = ResumeAgent(db, user_id)
            agent_result = await agent.run(
                {
                    "role_type": opp.type.lower() if opp else "internship",
                    "target_company": opp.company if opp else None,
                    "skills": opp.skills_required if opp else [],
                    "application_id": application_id,
                }
            )
            task.output = agent_result.output or {}
        else:
            task.output = {"error": "Application not found"}

        task.status = TaskStatus.completed
        task.completed_at = datetime.now(UTC)
        db.add(task)
        await db.commit()
    return task_id


async def dispatch_agent(
    agent_type: str,
    user_id: str,
    params: dict,
    db: AsyncSession,
    memory_context: dict | None = None,
) -> dict:
    """Dispatch a single agent via the AGENT_REGISTRY."""
    if memory_context:
        params["memory_context"] = memory_context

    factory = AGENT_REGISTRY.get(agent_type)
    if factory:
        agent = factory(db, user_id)
        result = await agent.run({**params, "memory_context": params.get("memory_context", {})})
        return result.output or {"error": result.error}
    return {"error": f"No handler for agent type: {agent_type}", "items": [], "total": 0}


async def run_planner_agent(user_id: str, goal: str) -> tuple[str, str | None]:
    """
    Run the full planner pipeline via the LangGraph StateGraph engine.

    This is the single unified entry point for planner execution.
    Delegates to ``run_planner_graph()`` in graph_engine.py which provides
    full LangSmith observability when ``LANGCHAIN_API_KEY`` is set.

    Returns (task_id, trace_url) for tracking and observability.
    """
    task_id = _gen_id()
    trace_url: str | None = None
    async with async_session_factory() as db:
        # Create and persist the planner task
        planner_goal = PlannerGoal(
            user_id=user_id,
            goal_text=goal,
            status="running",
            plan=[],
        )
        db.add(planner_goal)

        planner_task = AgentTaskModel(
            id=task_id,
            user_id=user_id,
            agent_type="planner",
            goal_id=planner_goal.id,
            input={"goal": goal},
            status=TaskStatus.running,
            started_at=datetime.now(UTC),
        )
        db.add(planner_task)
        await db.flush()

        try:
            # Run via the LangGraph StateGraph engine (with full LangSmith observability)
            from app.agents.graph_engine import run_planner_graph

            output = await run_planner_graph(db, user_id, goal)
            trace_url = output.get("trace_url")

            # Update planner task with results
            planner_task.status = TaskStatus.completed
            planner_task.output = output
            planner_task.completed_at = datetime.now(UTC)

            # Update planner goal
            planner_goal.status = "completed"
            planner_goal.completed_at = datetime.now(UTC)

            # Send notification
            await create_notification(
                db,
                user_id,
                title="Goal completed",
                body="Your goal has been processed.",
                type="success",
            )
        except Exception as e:
            planner_task.status = TaskStatus.failed
            planner_task.error = str(e)
            planner_task.completed_at = datetime.now(UTC)
            planner_goal.status = "failed"
            planner_goal.completed_at = datetime.now(UTC)
            logger.exception("Planner agent failed for user %s: %s", user_id, e)

        await db.commit()

    return task_id, trace_url
