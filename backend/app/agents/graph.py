"""
LangGraph agent orchestration for AgentForge Career OS.

This is a thin LangGraph wrapper that delegates all actual agent execution
to the OrchestratorAgent in orchestrator/service.py, which is the single
unified orchestrator for the system.

Architecture:
  START → decompose_goal → dispatch_all_agents (via OrchestratorAgent)
          → reflect_on_results → generate_final_response → END
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.agents.orchestrator.service import (
    OrchestratorAgent,
    _filter_tasks_by_context,
    _score_agent_output,
)
from app.agents.planner import decompose_goal_with_llm, format_planner_response
from app.agents.schemas import AgentStatus
from app.config import settings
from app.database import async_session_factory
from app.models.user import (
    AgentTask,
    AgentType,
    PlannerGoal,
    TaskStatus,
)
from app.services.memory_service import MemoryService
from app.services.notification_service import create_notification
from app.services.profile_service import ProfileService

logger = logging.getLogger("agentforge.graph")


def configure_langsmith() -> None:
    if settings.langchain_api_key:
        import os

        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.app_name.replace(" ", "-").lower())
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        logger.info("LangSmith tracing enabled (project=%s)", os.environ["LANGCHAIN_PROJECT"])


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Graph State Schema ─────────────────────────────────────


class PlannerGraphState(TypedDict):
    user_id: str
    goal: str
    profile: dict
    memory_context: dict
    tasks: list[dict]
    results: dict[str, Any]
    final_response: str
    error: str | None
    planner_goal_id: str | None
    planner_task_id: str | None
    reflection_scores: dict[str, dict]
    reflection_iterations: int
    needs_regeneration: bool


# ─── Node: Decompose Goal ───────────────────────────────────


async def decompose_goal_node(state: PlannerGraphState) -> dict:
    subtasks = await decompose_goal_with_llm(state["goal"], state["profile"], state["memory_context"])
    task_list = [dict(t) for t in subtasks]

    planner_task_id = gen_id()
    async with async_session_factory() as db:
        planner_goal = PlannerGoal(
            user_id=state["user_id"],
            goal_text=state["goal"],
            status="running",
            plan=task_list,
        )
        db.add(planner_goal)

        planner_task = AgentTask(
            id=planner_task_id,
            user_id=state["user_id"],
            agent_type=AgentType.planner,
            goal_id=planner_goal.id,
            input={"goal": state["goal"], "tasks": task_list},
            status=TaskStatus.running,
            started_at=datetime.now(UTC),
        )
        db.add(planner_task)
        await db.commit()

    return {
        "tasks": task_list,
        "planner_goal_id": str(planner_goal.id),
        "planner_task_id": planner_task_id,
        "error": None,
    }


# ─── Node: Dispatch All Agents (via OrchestratorAgent) ──────


async def dispatch_all_agents_node(state: PlannerGraphState) -> dict:
    tasks = state.get("tasks", [])
    if not tasks:
        return {"results": {}}

    tasks = _filter_tasks_by_context(tasks, state.get("profile", {}))
    if not tasks:
        return {"results": {}}

    tasks.sort(key=lambda t: t.get("priority", 5))

    # Delegate to OrchestratorAgent for actual execution
    async with async_session_factory() as db:
        orchestrator = OrchestratorAgent(db, state["user_id"])

        # Configure orchestrator to run these specific tasks
        orchestrator.results = {}
        memory_context = state.get("memory_context", {})

        # Execute each task in parallel using the orchestrator's parallel dispatch
        from app.agents.orchestrator.schemas import TaskDef

        task_defs = []
        for task_dict in tasks:
            td = TaskDef(
                agent=task_dict.get("agent", "monitor"),
                action=task_dict.get("action", ""),
                params=task_dict.get("params", {}),
                priority=task_dict.get("priority", 5),
            )
            td.params["memory_context"] = memory_context
            task_defs.append(td)

        await orchestrator._dispatch_parallel(task_defs, memory_context)

        # Convert results to dict format matching graph.py's expected output
        merged: dict[str, Any] = {}
        for agent_type, agent_res in orchestrator.results.items():
            if agent_res.status == AgentStatus.COMPLETED:
                merged[agent_type] = agent_res.output or {}
            else:
                merged[agent_type] = {"error": agent_res.error or "Unknown error"}

        return {"results": merged}


# ─── Node: Reflect on Results ───────────────────────────────


def should_regenerate(state: PlannerGraphState) -> str:
    if state.get("needs_regeneration") and state.get("reflection_iterations", 0) < 2:
        return "dispatch_all_agents"
    return "generate_final_response"


async def reflect_on_results_node(state: PlannerGraphState) -> dict:
    results = state.get("results", {})
    iteration = state.get("reflection_iterations", 0)
    reflection_scores = {}
    needs_regeneration = False
    profile_skills = state.get("profile", {}).get("skills", [])

    for agent_type, result in results.items():
        scores = _score_agent_output(agent_type, result, state["goal"], profile_skills)
        reflection_scores[agent_type] = scores
        if scores["total"] < 35 and iteration < 2:
            needs_regeneration = True

    return {
        "reflection_scores": reflection_scores,
        "needs_regeneration": needs_regeneration,
        "reflection_iterations": iteration + 1,
    }


# ─── Node: Generate Final Response ──────────────────────────


async def generate_final_response_node(state: PlannerGraphState) -> dict:
    final_response = format_planner_response(state["goal"], state.get("results", {}))
    async with async_session_factory() as db:
        if state.get("planner_goal_id"):
            result = await db.execute(select(PlannerGoal).where(PlannerGoal.id == state["planner_goal_id"]))
            pg = result.scalar_one_or_none()
            if pg:
                pg.status = "completed"
                pg.completed_at = datetime.now(UTC)
        if state.get("planner_task_id"):
            result = await db.execute(select(AgentTask).where(AgentTask.id == state["planner_task_id"]))
            pt = result.scalar_one_or_none()
            if pt:
                pt.status = TaskStatus.completed
                pt.output = {"results": state["results"], "final_response": final_response}
                pt.completed_at = datetime.now(UTC)
                await create_notification(
                    db,
                    state["user_id"],
                    title="Goal completed",
                    body="Your goal has been processed.",
                    type="success",
                )
        await db.commit()
    return {"final_response": final_response}


# ─── LangGraph Builder ──────────────────────────────────────


def build_planner_graph() -> StateGraph:
    builder = StateGraph(PlannerGraphState)
    builder.add_node("decompose_goal", decompose_goal_node)
    builder.add_node("dispatch_all_agents", dispatch_all_agents_node)
    builder.add_node("reflect_on_results", reflect_on_results_node)
    builder.add_node("generate_final_response", generate_final_response_node)
    builder.add_edge(START, "decompose_goal")
    builder.add_edge("decompose_goal", "dispatch_all_agents")
    builder.add_edge("dispatch_all_agents", "reflect_on_results")
    builder.add_conditional_edges(
        "reflect_on_results",
        should_regenerate,
        {"dispatch_all_agents": "dispatch_all_agents", "generate_final_response": "generate_final_response"},
    )
    builder.add_edge("generate_final_response", END)
    graph = builder.compile()
    configure_langsmith()
    return graph


_planner_graph_instance: StateGraph | None = None


def get_planner_graph() -> StateGraph:
    global _planner_graph_instance
    if _planner_graph_instance is None:
        _planner_graph_instance = build_planner_graph()
        logger.info("Planner LangGraph compiled and ready")
    return _planner_graph_instance


# ─── Top-Level Entry Points (delegate to OrchestratorAgent) ──


async def run_planner_agent(user_id: str, goal: str) -> str:
    """Run the full planner pipeline via the LangGraph."""
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
        "reflection_scores": {},
        "reflection_iterations": 0,
        "needs_regeneration": False,
    }

    graph = get_planner_graph()
    final_state = await graph.ainvoke(initial_state)
    return final_state.get("planner_task_id") or gen_id()
