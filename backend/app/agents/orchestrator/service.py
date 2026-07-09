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
from app.agents.planner import decompose_goal_with_llm
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.research_agent import ResearchAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.schemas import AgentResult, AgentStatus
from app.database import async_session_factory
from app.models.user import AgentTask as AgentTaskModel
from app.models.user import Application, Opportunity, PlannerGoal, TaskStatus
from app.services.memory_service import MemoryService
from app.services.notification_service import create_notification
from app.services.profile_service import ProfileService

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


# ── Reflection / Quality Scoring ────────────────────────────

REFLECTION_RUBRIC = {
    "accuracy": "No hallucinations, sources verifiable",
    "specificity": "Tailored to user, not generic",
    "actionability": "Contains next steps the user can actually take",
    "tone_match": "Matches the user's communication preferences",
    "format_quality": "Correct structure, no broken JSON, readable",
}


async def _score_agent_output(agent_type: str, result: dict, goal: str, profile_skills: list[str]) -> dict:
    scores = {}
    if not result or "error" in result:
        for dim in REFLECTION_RUBRIC:
            scores[dim] = 0
        scores["total"] = 0
        scores["feedback"] = "Agent returned error or empty result"
        return scores

    result_str = str(result)
    items = result.get("items", [])

    error_keywords = ["information not available", "error", "unavailable", "unknown"]
    accuracy = 10
    for kw in error_keywords:
        if kw in result_str.lower():
            accuracy -= 3
    if items:
        accuracy = min(10, accuracy + 2)
    if result.get("summary") and len(result.get("summary", "")) > 50:
        accuracy = min(10, accuracy + 1)
    scores["accuracy"] = max(1, accuracy)

    specificity = 4
    for skill in profile_skills:
        if isinstance(skill, str) and skill.lower() in result_str.lower():
            specificity += 1
    if items:
        specificity += 2
    if goal.lower() in result_str.lower():
        specificity += 1
    scores["specificity"] = min(10, specificity)

    actionability = 5
    if items:
        actionability = 8
    if result.get("action_items") or result.get("next_steps"):
        actionability = min(10, actionability + 2)
    if result.get("tips") or result.get("suggestions"):
        actionability = min(10, actionability + 1)
    scores["actionability"] = actionability

    tone_markers = ["recommend", "suggest", "consider", "based on", "opportunity", "skill"]
    tone = 6
    for marker in tone_markers:
        if marker in result_str.lower():
            tone += 1
    scores["tone_match"] = min(10, tone)

    fmt = 4
    if isinstance(result, dict):
        fmt = 6
        if "items" in result or "questions" in result or "guidance" in result:
            fmt += 2
    scores["format_quality"] = min(10, fmt)

    scores["total"] = sum(v for k, v in scores.items() if k != "total")
    weaknesses = [
        f"{dim} is low ({sc}/10)" for dim, sc in scores.items() if dim not in ("total", "feedback") and sc < 5
    ]
    scores["feedback"] = "; ".join(weaknesses) if weaknesses else f"{agent_type}: Output quality acceptable"
    return scores


# ── Dynamic Routing ─────────────────────────────────────────


def _filter_tasks_by_context(tasks: list[dict], profile: dict) -> list[dict]:
    role_types = profile.get("role_types", [])
    target_locations = profile.get("target_locations", [])
    career_goal = profile.get("career_goal", "").lower()

    filtered: list[dict] = []
    for task in tasks:
        agent = task.get("agent", "")
        if agent == "internship" and role_types:
            if all("intern" not in rt.lower() for rt in role_types):
                continue
        if agent == "job" and role_types:
            if all("full" not in rt.lower() and "job" not in rt.lower() for rt in role_types):
                if any("intern" in rt.lower() for rt in role_types):
                    continue
        if agent == "research":
            query = task.get("params", {}).get("query", "")
            if not query and not target_locations:
                continue
        params = task.get("params", {})
        if career_goal and "career_goal" not in params:
            params["career_goal"] = career_goal
        task["params"] = params
        filtered.append(task)
    return filtered


# ── Main Orchestrator Agent ─────────────────────────────────


class OrchestratorAgent(BaseAgent):
    agent_type = "orchestrator"

    def __init__(self, db: AsyncSession, user_id: str):
        super().__init__(db, user_id)
        self.run_id: str = str(uuid.uuid4())
        self.results: dict[str, AgentResult] = {}

    async def execute(self, params: dict) -> dict:
        goal = params.get("goal", "")
        mode = params.get("mode", "parallel")

        if not goal:
            return {"error": "No goal provided", "run_id": self.run_id}

        profile_service = ProfileService(self.db)
        memory_service = MemoryService(self.db)

        profile = await profile_service.get_or_create_profile(self.user_id)
        profile_skills = await profile_service.get_skill_names(profile.id)
        profile_dict = {
            "id": str(profile.id),
            "skills": profile_skills,
            "target_locations": profile.target_locations or [],
            "role_types": profile.role_types or [],
            "career_goal": profile.career_goal or "",
        }
        memory_context = await memory_service.get_user_context(self.user_id)

        subtasks = await decompose_goal_with_llm(goal, profile_dict, memory_context)
        if not subtasks:
            return {
                "run_id": self.run_id,
                "goal": goal,
                "status": "completed",
                "results": {
                    "guidance": {"message": "No specific tasks identified", "goal": goal},
                },
            }

        task_defs = [TaskDef(**t) for t in subtasks]
        task_defs.sort(key=lambda t: t.priority)

        # Filter tasks by user profile context
        task_dicts = [t.model_dump() for t in task_defs]
        filtered = _filter_tasks_by_context(task_dicts, profile_dict)
        task_defs = [TaskDef(**t) for t in filtered]

        await self._persist_plan(goal, task_defs)

        if mode == "parallel":
            await self._dispatch_parallel(task_defs, memory_context)
        else:
            await self._dispatch_sequential(task_defs, memory_context)

        # Run reflection scoring on results
        reflection_scores = {}
        for agent_key, agent_res in self.results.items():
            reflection_scores[agent_key] = _score_agent_output(
                agent_key,
                agent_res.output or {"error": agent_res.error} if agent_res.error else (agent_res.output or {}),
                goal,
                profile_skills,
            )

        await self._persist_results()

        flat = {}
        for k, v in self.results.items():
            flat[k] = {
                "status": v.status,
                "message": ((v.output or {}).get("message", str(v.output)[:200]) if v.output else v.error),
                "duration_ms": v.duration_ms,
            }

        return {
            "run_id": self.run_id,
            "goal": goal,
            "status": "completed",
            "results": flat,
            "reflection_scores": reflection_scores,
            "detail": {k: v.output for k, v in self.results.items() if v.output and v.status == AgentStatus.COMPLETED},
        }

    # ── Parallel Dispatch ────────────────────────────────────

    async def _dispatch_parallel(
        self,
        task_defs: list[TaskDef],
        memory_context: dict,
    ) -> None:
        coros = []
        for td in task_defs:
            td.params["memory_context"] = memory_context
            coros.append(self._execute_single_agent(td))

        results_list = await asyncio.gather(*coros, return_exceptions=True)

        for item in results_list:
            if isinstance(item, Exception):
                logger.warning("Parallel agent dispatch raised exception: %s", item)
                continue
            if isinstance(item, AgentResult):
                self.results[item.agent_type] = item
            elif isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, AgentResult):
                        self.results[k] = v
                    elif isinstance(v, dict) and "error" not in v:
                        self.results[k] = AgentResult(
                            agent_type=k,
                            status=AgentStatus.COMPLETED,
                            output=v,
                        )
                    elif isinstance(v, dict) and "error" in v:
                        self.results[k] = AgentResult(
                            agent_type=k,
                            status=AgentStatus.FAILED,
                            error=v["error"],
                        )

    # ── Sequential Dispatch ──────────────────────────────────

    async def _dispatch_sequential(
        self,
        task_defs: list[TaskDef],
        memory_context: dict,
    ) -> None:
        for td in task_defs:
            agent_type = td.agent
            logger.info("Orchestrator dispatching %s (priority %s)", agent_type, td.priority)

            factory = AGENT_REGISTRY.get(agent_type)
            if factory:
                agent = factory(self.db, self.user_id)
                td.params["memory_context"] = memory_context
                td.params["action"] = td.params.get("action", td.action)
                agent_result = await self._run_class_agent(agent_type, agent, td.params)
                self.results[agent_type] = agent_result
            else:
                self.results[agent_type] = AgentResult(
                    agent_type=agent_type,
                    status=AgentStatus.SKIPPED,
                    error=f"No handler for agent type: {agent_type}",
                )

    # ── Single Agent Execution (for parallel dispatch) ───────

    async def _execute_single_agent(self, td: TaskDef) -> AgentResult:
        """Execute a single task definition with retry and per-agent DB session."""
        agent_type = td.agent
        factory = AGENT_REGISTRY.get(agent_type)
        if factory:
            agent = factory(self.db, self.user_id)
            return await self._run_class_agent(agent_type, agent, td.params)
        return AgentResult(
            agent_type=agent_type,
            status=AgentStatus.SKIPPED,
            error=f"No handler for agent type: {agent_type}",
        )

    # ── Agent Execution Wrappers ─────────────────────────────

    async def _run_class_agent(
        self,
        agent_type: str,
        agent: BaseAgent,
        params: dict,
    ) -> AgentResult:
        try:
            return await _run_with_retry(
                lambda: agent.run(params),
                f"class_agent:{agent_type}",
            )
        except Exception as e:
            logger.exception("Agent %s permanently failed: %s", agent_type, e)
            return AgentResult(
                agent_type=agent_type,
                status=AgentStatus.FAILED,
                error=str(e),
            )

    # ── Persistence Helpers ──────────────────────────────────

    async def _persist_plan(self, goal: str, tasks: list[TaskDef]) -> None:
        try:
            pg = PlannerGoal(
                user_id=self.user_id,
                goal_text=goal,
                plan=[dict(t) for t in tasks],
                status="running",
            )
            self.db.add(pg)
            await self.db.flush()
        except Exception as e:
            logger.debug("Failed to persist plan: %s", e)

    async def _persist_results(self) -> None:
        try:
            for agent_type, result in self.results.items():
                task = AgentTaskModel(
                    user_id=self.user_id,
                    agent_type=agent_type,
                    input={},
                    output=result.output or {},
                    status=(TaskStatus.completed if result.status == AgentStatus.COMPLETED else TaskStatus.failed),
                    error=result.error,
                )
                self.db.add(task)
            await self.db.flush()
        except Exception as e:
            logger.debug("Failed to persist results: %s", e)


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
