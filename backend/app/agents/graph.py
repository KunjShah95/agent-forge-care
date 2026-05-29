"""
LangGraph agent orchestration for AgentForge Career OS.

Defines the state graph that routes user goals through the planner
and specialist agents, then stores results back to the database.

Architecture:
  START → decompose_goal → dispatch_all_agents (parallel via asyncio.gather)
          → generate_final_response → END

The actual agent logic lives in dedicated files:
  - internship_agent.py   → Internship discovery and matching
  - job_agent.py          → Full-time/grad role discovery and matching
  - research_agent.py     → Company research, interview insights, market intel
  - assistant_agent.py    → Resume, interview prep, networking, monitoring, guidance

LangSmith tracing is enabled when LANGCHAIN_API_KEY is set in the environment.
"""

import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.user import (
    AgentTask, AgentType, TaskStatus, PlannerGoal, Opportunity,
)
from app.agents.planner import decompose_goal_with_llm, format_planner_response
from app.agents.internship_agent import discover_internships
from app.agents.job_agent import discover_jobs
from app.agents.research_agent import conduct_research
from app.agents.assistant_agent import (
    tailor_resume, generate_cover_letter, prepare_interview,
    generate_outreach, run_daily_scan, get_career_guidance,
)
from app.utils.demo_data import generate_demo_opportunities
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService

logger = logging.getLogger("agentforge.graph")


# ─── LangSmith Tracing ─────────────────────────────────────


def configure_langsmith() -> None:
    """
    Configure LangSmith tracing if environment variables are set.
    Call once at startup before any graph invocations.

    Required env vars:
      - LANGCHAIN_TRACING_V2=true
      - LANGCHAIN_API_KEY=ls__...
    Optional env vars:
      - LANGCHAIN_PROJECT=agentforge
      - LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
    """
    if settings.langchain_api_key:
        import os
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.app_name.replace(" ", "-").lower())
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        logger.info("LangSmith tracing enabled (project=%s)", os.environ["LANGCHAIN_PROJECT"])


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Agent Map (shared across nodes) ────────────────────────

AGENT_HANDLERS = {
    AgentType.internship: discover_internships,
    AgentType.job: discover_jobs,
    AgentType.research: conduct_research,
    AgentType.resume: tailor_resume,
    AgentType.interview: prepare_interview,
    AgentType.networking: generate_outreach,
    AgentType.monitor: run_daily_scan,
    AgentType.planner: get_career_guidance,
}


# ─── Graph State Schema ─────────────────────────────────────


class PlannerGraphState(TypedDict):
    """Shared state passed through the LangGraph."""
    user_id: str
    goal: str
    profile: dict
    memory_context: dict
    tasks: list[dict]
    results: dict[str, Any]
    final_response: str
    error: Optional[str]
    planner_goal_id: Optional[str]
    planner_task_id: Optional[str]


# ─── Node: Decompose Goal ───────────────────────────────────


async def decompose_goal_node(state: PlannerGraphState) -> dict:
    """
    Graph node: decompose the user's goal into specialist agent tasks
    using LLM (preferred) or keyword fallback.
    Creates the PlannerGoal and AgentTask records in the database.
    """
    user_id = state["user_id"]
    goal = state["goal"]
    profile = state["profile"]
    memory_context = state["memory_context"]

    # Use async LLM-aware decomposition
    subtasks = await decompose_goal_with_llm(goal, profile, memory_context)
    task_list = [dict(t) for t in subtasks]

    # Persist to database
    planner_task_id = gen_id()
    async with async_session_factory() as db:
        planner_goal = PlannerGoal(
            user_id=user_id,
            goal_text=goal,
            status="running",
            plan=task_list,
        )
        db.add(planner_goal)
        await db.flush()

        planner_task = AgentTask(
            id=planner_task_id,
            user_id=user_id,
            agent_type=AgentType.planner,
            goal_id=planner_goal.id,
            input={"goal": goal, "tasks": task_list},
            status=TaskStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        db.add(planner_task)
        await db.flush()

    return {
        "tasks": task_list,
        "planner_goal_id": str(planner_goal.id),
        "planner_task_id": planner_task_id,
        "error": None,
    }


# ─── Parallel Agent Dispatch Helpers ────────────────────────


async def _execute_single_agent(
    agent_str: str,
    user_id: str,
    params: dict,
    planner_goal_id: str | None,
) -> dict:
    """
    Execute a single specialist agent in its own DB session.
    This enables true parallel execution via asyncio.gather().
    """
    from app.database import async_session_factory
    from app.models.user import AgentTask, TaskStatus

    try:
        agent_type = AgentType(agent_str)
    except ValueError:
        agent_type = AgentType.monitor

    handler = AGENT_HANDLERS.get(agent_type)
    specialist_task_id = gen_id()

    # Each agent gets its own DB session to avoid session sharing conflicts
    async with async_session_factory() as db:
        spec_task = AgentTask(
            id=specialist_task_id,
            user_id=user_id,
            agent_type=agent_type,
            goal_id=planner_goal_id,
            input=params,
            status=TaskStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        db.add(spec_task)
        await db.flush()

        try:
            if handler:
                agent_result = await handler(user_id, params, db)
            else:
                agent_result = await _fallback_search(user_id, params, db, agent_type)

            spec_task.status = TaskStatus.completed
            spec_task.output = agent_result
            spec_task.completed_at = datetime.now(timezone.utc)

            return {agent_str: agent_result}

        except Exception as e:
            logger.warning("Agent %s failed: %s", agent_str, e)
            spec_task.status = TaskStatus.failed
            spec_task.error = str(e)
            spec_task.completed_at = datetime.now(timezone.utc)

            return {agent_str: {"error": str(e)}}

    # Should not reach here, but just in case
    return {agent_str: {"error": "Unknown execution error"}}


async def dispatch_all_agents_node(state: PlannerGraphState) -> dict:
    """
    Graph node: dispatch all specialist agents in parallel using asyncio.gather().

    Each agent runs with its own database session to allow true parallel execution.
    Results are aggregated into a single dict keyed by agent name.
    Falls back to sequential execution if tasks are empty.
    """
    user_id = state["user_id"]
    tasks = state.get("tasks", [])
    planner_goal_id = state.get("planner_goal_id")

    if not tasks:
        return {"results": {}}

    logger.info("Dispatching %d specialist agents in parallel", len(tasks))

    # Create coroutines for all agents
    coros = []
    for task_def in tasks:
        agent_str = task_def.get("agent", "monitor")
        params = task_def.get("params", {})
        coro = _execute_single_agent(agent_str, user_id, params, planner_goal_id)
        coros.append(coro)

    # Execute all agents in parallel — use return_exceptions=True so one
    # agent crash doesn't discard results from all other agents
    results_list = await asyncio.gather(*coros, return_exceptions=True)

    # Merge individual results into a single dict, handling exceptions
    merged_results: dict[str, Any] = {}
    for result_item in results_list:
        if isinstance(result_item, Exception):
            logger.warning("Agent execution raised exception: %s", result_item)
            merged_results["error"] = {"error": str(result_item)}
        else:
            merged_results.update(result_item)

    logger.info(
        "Parallel dispatch complete: %d succeeded, %d failed",
        sum(1 for v in merged_results.values() if isinstance(v, dict) and "error" not in v),
        sum(1 for v in merged_results.values() if isinstance(v, dict) and "error" in v),
    )

    return {"results": merged_results}


async def _fallback_search(
    user_id: str, params: dict, db: AsyncSession, agent_type: AgentType
) -> dict:
    """Fallback search for unknown agent types."""
    from app.search.adapters import SearchAdapter

    search_adapter = SearchAdapter()
    query = params.get("query", "")
    location = params.get("location")

    try:
        raw_results = await search_adapter.search(query=query, location=location)
    except Exception:
        raw_results = generate_demo_opportunities(agent_type, query, location)

    items = []
    for r in raw_results[:10]:
        opp = Opportunity(
            user_id=user_id,
            title=r.get("title", "Untitled"),
            company=r.get("company", "Unknown"),
            location=r.get("location"),
            remote=r.get("remote", False),
            type=r.get("type", agent_type.value.capitalize()),
            description=r.get("description"),
            apply_url=r.get("apply_url"),
            skills_required=r.get("skills", params.get("skills", [])),
            source=r.get("source", agent_type.value),
        )
        db.add(opp)
        await db.flush()
        items.append({"id": str(opp.id), "title": opp.title, "company": opp.company})

    return {"items": items, "total": len(items)}


# ─── Standalone Agent Dispatcher ────────────────────────────


async def dispatch_agent(
    agent_type: AgentType, user_id: str, params: dict, db: AsyncSession
) -> dict:
    """
    Dispatch a single specialist agent task and return its result.
    Used by the streaming chat endpoint (chat.py) for sequential dispatch.
    """
    handler = AGENT_HANDLERS.get(agent_type)
    if handler:
        return await handler(user_id, params, db)
    return await _fallback_search(user_id, params, db, agent_type)


# ─── Node: Generate Final Response ──────────────────────────


async def generate_final_response_node(state: PlannerGraphState) -> dict:
    """
    Graph node: produce the final planner response and update DB records.
    """
    goal = state["goal"]
    results = state.get("results", {})

    final_response = format_planner_response(goal, results)

    # Update database records to completed
    planner_task_id = state.get("planner_task_id")
    planner_goal_id = state.get("planner_goal_id")

    async with async_session_factory() as db:
        from sqlalchemy import select

        if planner_goal_id:
            result = await db.execute(
                select(PlannerGoal).where(PlannerGoal.id == planner_goal_id)
            )
            planner_goal = result.scalar_one_or_none()
            if planner_goal:
                planner_goal.status = "completed"
                planner_goal.completed_at = datetime.now(timezone.utc)

        if planner_task_id:
            result = await db.execute(
                select(AgentTask).where(AgentTask.id == planner_task_id)
            )
            planner_task = result.scalar_one_or_none()
            if planner_task:
                planner_task.status = TaskStatus.completed
                planner_task.output = {
                    "results": results,
                    "final_response": final_response,
                }
                planner_task.completed_at = datetime.now(timezone.utc)

        await db.flush()

    return {
        "final_response": final_response,
    }


# ─── Build the LangGraph ────────────────────────────────────


def build_planner_graph() -> StateGraph:
    """
    Build and return the compiled planner graph.

    Architecture:
        START → decompose_goal → dispatch_all_agents → generate_final_response → END

    Node details:
      1. decompose_goal          — LLM-powered goal decomposition into specialist tasks
      2. dispatch_all_agents      — parallel execution via asyncio.gather()
      3. generate_final_response  — formats output, updates DB records
    """
    builder = StateGraph(PlannerGraphState)

    builder.add_node("decompose_goal", decompose_goal_node)
    builder.add_node("dispatch_all_agents", dispatch_all_agents_node)
    builder.add_node("generate_final_response", generate_final_response_node)

    builder.add_edge(START, "decompose_goal")
    builder.add_edge("decompose_goal", "dispatch_all_agents")
    builder.add_edge("dispatch_all_agents", "generate_final_response")
    builder.add_edge("generate_final_response", END)

    graph = builder.compile()

    # Configure LangSmith tracing at compile time
    configure_langsmith()

    return graph


# Lazy singleton — compiled only on first use, not at import time
_planner_graph_instance: StateGraph | None = None


def get_planner_graph() -> StateGraph:
    """Get or create the compiled planner graph singleton."""
    global _planner_graph_instance
    if _planner_graph_instance is None:
        _planner_graph_instance = build_planner_graph()
        logger.info("Planner LangGraph compiled and ready")
    return _planner_graph_instance


# ─── Main Planner Entry Point ───────────────────────────────


async def run_planner_agent(user_id: str, goal: str) -> str:
    """
    Main entry point: run the planner graph for a user goal.
    Invokes the compiled LangGraph and returns the planner task ID.

    Preserves the same signature for backward compatibility
    with the API routes in app.api.v1.agents.
    """

    async with async_session_factory() as db:
        profile_service = ProfileService(db)
        profile = await profile_service.get_or_create_profile(user_id)
        profile_skills = await profile_service.get_skill_names(profile.id)

        memory_service = MemoryService(db)
        memory_context = await memory_service.get_user_context(user_id)

        profile_dict = {
            "id": str(profile.id),
            "skills": profile_skills,
            "target_locations": profile.target_locations or [],
            "role_types": profile.role_types or [],
            "career_goal": profile.career_goal or "",
        }

    # Initial state — the graph handles all DB persistence internally
    initial_state: PlannerGraphState = {
        "user_id": user_id,
        "goal": goal,
        "profile": profile_dict,
        "memory_context": memory_context,
        "tasks": [],
        "results": {},
        "final_response": "",
        "error": None,
        "planner_goal_id": None,
        "planner_task_id": None,
    }

    # Invoke the LangGraph (lazy-compiled singleton)
    graph = get_planner_graph()
    final_state = await graph.ainvoke(initial_state)

    # Return the planner task ID so callers can poll status
    return final_state.get("planner_task_id") or gen_id()


# ─── Direct API Entry Points ────────────────────────────────


async def run_opportunity_scan(user_id: str) -> str:
    """Run the opportunity monitor to scan for new openings."""
    task_id = gen_id()

    async with async_session_factory() as db:
        task = AgentTask(
            id=task_id,
            user_id=user_id,
            agent_type=AgentType.monitor,
            input={"action": "scan"},
            status=TaskStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()

        try:
            result = await run_daily_scan(user_id, {"action": "scan"}, db)

            task.status = TaskStatus.completed
            task.output = result
            task.completed_at = datetime.now(timezone.utc)
            await db.flush()

        except Exception as e:
            task.status = TaskStatus.failed
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await db.flush()

    return task_id


async def run_resume_tailoring(user_id: str, application_id: str) -> str:
    """Tailor resume for a specific application."""
    task_id = gen_id()

    async with async_session_factory() as db:
        from app.models.user import Application
        from sqlalchemy import select

        result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = result.scalar_one_or_none()

        task = AgentTask(
            id=task_id,
            user_id=user_id,
            agent_type=AgentType.resume,
            input={"application_id": application_id},
            status=TaskStatus.completed,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        if app:
            # Get opportunity details for context
            opp_result = await db.execute(
                select(Opportunity).where(Opportunity.id == app.opportunity_id)
            )
            opp = opp_result.scalar_one_or_none()
            result = await tailor_resume(user_id, {
                "role_type": opp.type.lower() if opp else "internship",
                "target_company": opp.company if opp else None,
                "skills": opp.skills_required if opp else [],
                "application_id": application_id,
            }, db)
            task.output = result
        else:
            task.output = {"error": "Application not found"}

        db.add(task)
        await db.flush()

    return task_id
