"""
LangGraph agent orchestration for AgentForge Career OS.

This is the primary entry point for the LangGraph-based planner pipeline.
It delegates to ``graph_engine.py`` for the actual StateGraph definition,
and re-exports all legacy symbols for backward compatibility.

Pipeline (visible in LangSmith UI when ``LANGCHAIN_API_KEY`` is set):
  1. load_context      → Fetch user profile, skills, memory
  2. decompose_goal    → LLM breakdown into subtasks
  3. filter_tasks      → Remove irrelevant tasks
  4. dispatch_agents   → Parallel agent execution
  5. reflect            → Score + regenerate low-quality outputs
  6. format_output     → Build final response

Usage:
    graph = get_planner_graph()
    state = PlannerGraphState(user_id="...", goal="...")
    result = await graph.ainvoke(state)
"""

import logging
import uuid
import warnings
from typing import Any

from app.agents.graph_engine import (
    PlannerState,
    _filter_tasks_by_context,
    _score_agent_output,
    _get_compiled_graph,
    run_planner_graph,
)
from app.agents.orchestrator.service import (
    OrchestratorAgent,
    _run_with_retry,
    dispatch_agent,
    run_opportunity_scan,
    run_planner_agent,
    run_resume_tailoring,
)
from app.database import async_session_factory

logger = logging.getLogger("agentforge.graph")


# ─── Legacy Types (backward compat) ─────────────────--------


def _gen_id() -> str:
    return str(uuid.uuid4())


class PlannerGraphState(dict):
    """
    Backward-compatible TypedDict-like state for the planner pipeline.

    Legacy callers still using ``build_planner_graph().ainvoke(state)`` will
    receive a ``PlannerGraphState``-compatible dict from ``SimpleGraphWrapper``.
    New code should use ``run_planner_graph(db, user_id, goal)`` directly.
    """

    def __init__(
        self,
        user_id: str = "",
        goal: str = "",
        profile: dict | None = None,
        memory_context: dict | None = None,
        tasks: list[dict] | None = None,
        results: dict[str, Any] | None = None,
        final_response: str = "",
        error: str | None = None,
        planner_goal_id: str | None = None,
        planner_task_id: str | None = None,
        reflection_scores: dict[str, dict] | None = None,
        reflection_iterations: int = 0,
        needs_regeneration: bool = False,
    ):
        super().__init__()
        self["user_id"] = user_id
        self["goal"] = goal
        self["profile"] = profile or {}
        self["memory_context"] = memory_context or {}
        self["tasks"] = tasks or []
        self["results"] = results or {}
        self["final_response"] = final_response
        self["error"] = error
        self["planner_goal_id"] = planner_goal_id
        self["planner_task_id"] = planner_task_id
        self["reflection_scores"] = reflection_scores or {}
        self["reflection_iterations"] = reflection_iterations
        self["needs_regeneration"] = needs_regeneration

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key, default)


# ─── Legacy Functions (backward compat) ─────────────────────


def configure_langsmith() -> None:
    """No-op. LangSmith is configured automatically via env vars and main.py."""
    pass


def should_regenerate(state: PlannerGraphState) -> str:
    """
    Deprecated. The reflection loop now lives inside the LangGraph StateGraph
    as the ``reflect`` node with conditional edges.
    """
    if state.get("needs_regeneration") and state.get("reflection_iterations", 0) < 2:
        return "dispatch_all_agents"
    return "generate_final_response"


# ─── Graph Builder (primary entry point) ────────────────────


def build_planner_graph(db_session: Any = None) -> "PlannerGraphWrapper":
    """Build the LangGraph planner graph.

    Args:
        db_session: Optional DB session. If omitted, one will be created
                    inside each invocation (legacy behavior).

    Returns a ``PlannerGraphWrapper`` that wraps the compiled LangGraph
    StateGraph and delegates calls to it.
    """
    return PlannerGraphWrapper(pre_created_session=db_session)


def get_planner_graph(db_session: Any = None) -> "PlannerGraphWrapper":
    """Get the planner graph (alias for ``build_planner_graph``)."""
    return build_planner_graph(db_session)


# ─── Graph Wrapper ──────────────────────────────────────────


class PlannerGraphWrapper:
    """
    Wraps the compiled LangGraph StateGraph with a convenient interface.

    - ``ainvoke(state)`` runs the full pipeline and returns a dict compatible
      with the legacy ``PlannerGraphState`` format.
    - ``stream(state)`` yields intermediate state updates (for real-time UIs).
    """

    def __init__(self, pre_created_session=None):
        self._session = pre_created_session

    async def ainvoke(self, initial_state: PlannerGraphState) -> dict:
        """Run the full planner pipeline via LangGraph."""
        user_id = initial_state.get("user_id", "")
        goal = initial_state.get("goal", "")

        async def _run(session):
            output = await run_planner_graph(session, user_id, goal)
            return self._state_to_result(output, initial_state)

        if self._session:
            return await _run(self._session)

        async with async_session_factory() as db:
            return await _run(db)

    async def stream(self, initial_state: PlannerGraphState):
        """Stream intermediate state updates (for real-time UIs)."""
        from app.agents.graph_engine import _db_var

        user_id = initial_state.get("user_id", "")
        goal = initial_state.get("goal", "")

        async with async_session_factory() as db:
            token = _db_var.set(db)
            try:
                graph = await _get_compiled_graph()
                config = {
                    "configurable": {"thread_id": f"planner:{user_id}"},
                    "tags": ["planner", "agentforge"],
                    "metadata": {"user_id": user_id},
                }

                pstate: PlannerState = {
                    "user_id": user_id,
                    "goal": goal,
                    "profile": {},
                    "profile_skills": [],
                    "memory_context": {},
                    "task_defs": [],
                    "agent_results": {},
                    "reflection_scores": {},
                    "reflection_iterations": 0,
                    "final_output": {},
                    "error": None,
                }

                async for event in graph.astream(pstate, config):
                    yield event
            finally:
                _db_var.reset(token)

    def _state_to_result(self, output: dict, initial_state: PlannerGraphState) -> dict:
        """Convert ``run_planner_graph`` output to legacy ``PlannerGraphState`` format."""
        results = output.get("results", {})
        reflection_scores = output.get("reflection_scores", {})
        detail = output.get("detail", {})

        return {
            "user_id": initial_state.get("user_id", ""),
            "goal": initial_state.get("goal", ""),
            "profile": initial_state.get("profile", {}),
            "memory_context": initial_state.get("memory_context", {}),
            "tasks": initial_state.get("tasks", []),
            "results": results,
            "final_response": self._format_response(
                initial_state.get("goal", ""),
                results,
            ),
            "error": output.get("error"),
            "trace_url": output.get("trace_url"),
            "planner_goal_id": initial_state.get("planner_goal_id"),
            "planner_task_id": initial_state.get("planner_task_id") or _gen_id(),
            "reflection_scores": reflection_scores,
            "reflection_iterations": len(reflection_scores),
            "needs_regeneration": False,
        }

    def _format_response(self, goal: str, results: dict) -> str:
        """Format a final response string from agent results."""
        from app.agents.planner import format_planner_response

        return format_planner_response(goal, results)
