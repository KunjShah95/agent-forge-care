"""
LangGraph StateGraph engine for AgentForge Career OS.

This module replaces the earlier custom ``OrchestratorAgent`` with a proper
LangGraph StateGraph that provides full observability via LangSmith tracing
when ``LANGCHAIN_API_KEY`` is configured.

Pipeline steps (visible in LangSmith UI):
  1. load_context      — Fetch user profile, skills, memory from DB
  2. decompose_goal    — LLM breakdown of the goal into subtasks
  3. filter_tasks      — Prune tasks irrelevant to the user's profile
  4. dispatch_agents   — Parallel execution of all subtask agents
  5. reflect            — Score outputs; conditional edge retries low-quality
                          results (up to 2 iterations)
  6. format_output     — Build the final response dict
"""

import asyncio
import contextvars
import logging
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

# Per-run DB session — avoids putting non-serializable AsyncSession into state.
_db_var: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar("_db_var")

from app.agents.orchestrator.schemas import TaskDef
from app.agents.planner import decompose_goal_with_llm
from app.agents.schemas import AgentResult, AgentStatus
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService

logger = logging.getLogger("agentforge.graph_engine")

# ── Constants ───────────────────────────────────────────────

MAX_REFLECTION_ITERATIONS = 2
QUALITY_THRESHOLD = 35

REFLECTION_RUBRIC = {
    "accuracy": "No hallucinations, sources verifiable",
    "specificity": "Tailored to user, not generic",
    "actionability": "Contains next steps the user can actually take",
    "tone_match": "Matches the user's communication preferences",
    "format_quality": "Correct structure, no broken JSON, readable",
}


# ── State TypedDict ─────────────────────────────────────────


class PlannerState(TypedDict):
    """State passed between LangGraph nodes during planner execution."""

    user_id: str
    goal: str
    profile: dict
    profile_skills: list[str]
    memory_context: dict
    task_defs: list[dict]
    agent_results: dict[str, AgentResult]
    reflection_scores: dict[str, dict]
    reflection_iterations: int
    final_output: dict
    error: str | None



# ── Scoring Helper ──────────────────────────────────────────


async def _score_agent_output(
    agent_type: str,
    result: dict,
    goal: str,
    profile_skills: list[str],
) -> dict:
    """Score a single agent's output on a 5-dimension rubric (max 50)."""
    scores: dict[str, Any] = {}
    if not result or "error" in result:
        for dim in REFLECTION_RUBRIC:
            scores[dim] = 0
        scores["total"] = 0
        scores["feedback"] = "Agent returned error or empty result"
        return scores

    result_str = str(result)
    items = result.get("items", [])

    # accuracy
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

    # specificity
    specificity = 4
    for skill in profile_skills:
        if isinstance(skill, str) and skill.lower() in result_str.lower():
            specificity += 1
    if items:
        specificity += 2
    if goal.lower() in result_str.lower():
        specificity += 1
    scores["specificity"] = min(10, specificity)

    # actionability
    actionability = 5
    if items:
        actionability = 8
    if result.get("action_items") or result.get("next_steps"):
        actionability = min(10, actionability + 2)
    if result.get("tips") or result.get("suggestions"):
        actionability = min(10, actionability + 1)
    scores["actionability"] = actionability

    # tone_match
    tone_markers = ["recommend", "suggest", "consider", "based on", "opportunity", "skill"]
    tone = 6
    for marker in tone_markers:
        if marker in result_str.lower():
            tone += 1
    scores["tone_match"] = min(10, tone)

    # format_quality
    fmt = 4
    if isinstance(result, dict):
        fmt = 6
        if "items" in result or "questions" in result or "guidance" in result:
            fmt += 2
    scores["format_quality"] = min(10, fmt)

    scores["total"] = sum(v for k, v in scores.items() if k != "total")
    weaknesses = [
        f"{dim} is low ({sc}/10)"
        for dim, sc in scores.items()
        if dim not in ("total", "feedback") and sc < 5
    ]
    scores["feedback"] = "; ".join(weaknesses) if weaknesses else f"{agent_type}: Output quality acceptable"
    return scores


def _filter_tasks_by_context(tasks: list[dict], profile: dict) -> list[dict]:
    """Remove tasks irrelevant to the user's profile (e.g. internships for non-students)."""
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


# ── Graph Node Builders ─────────────────────────────────────
# Nodes read the DB session from _db_var contextvar so the graph
# structure has no closure over a session — making it fully cacheable.


async def _load_context(state: PlannerState) -> dict:
    """Fetch profile, skills, and memory context from the database."""
    user_id = state["user_id"]
    db = _db_var.get()
    try:
        profile_service = ProfileService(db)
        memory_service = MemoryService(db)

        profile = await profile_service.get_or_create_profile(user_id)
        profile_skills = await profile_service.get_skill_names(profile.id)
        memory_context = await memory_service.get_user_context(user_id)

        profile_dict = {
            "id": str(profile.id),
            "skills": profile_skills,
            "target_locations": profile.target_locations or [],
            "role_types": profile.role_types or [],
            "career_goal": profile.career_goal or "",
        }

        logger.info("load_context: profile loaded for user %s", user_id)
        return {
            "profile": profile_dict,
            "profile_skills": profile_skills,
            "memory_context": memory_context,
            "error": None,
        }
    except Exception as e:
        logger.exception("load_context failed for user %s: %s", user_id, e)
        return {"error": str(e)}


async def _decompose_goal(state: PlannerState) -> dict:
    """Decompose the user's goal into structured subtasks via LLM."""
    goal = state["goal"]
    profile = state.get("profile", {})
    memory_context = state.get("memory_context", {})

    try:
        subtasks = await decompose_goal_with_llm(goal, profile, memory_context)
        task_defs = [TaskDef(**t) for t in (subtasks or [])]
        task_defs.sort(key=lambda t: t.priority)
        logger.info("decompose_goal: %d task(s) identified", len(task_defs))
        return {"task_defs": [t.model_dump() for t in task_defs]}
    except Exception as e:
        logger.exception("decompose_goal failed: %s", e)
        return {"error": f"Goal decomposition failed: {e}"}


async def _filter_tasks(state: PlannerState) -> dict:
    """Prune tasks irrelevant to the user's profile."""
    task_defs = state.get("task_defs", [])
    profile = state.get("profile", {})

    if not task_defs:
        return {}

    filtered = _filter_tasks_by_context(task_defs, profile)
    logger.info("filter_tasks: %d → %d task(s) after profile filtering", len(task_defs), len(filtered))
    return {"task_defs": filtered}


async def _dispatch_agents(state: PlannerState) -> dict:
    """Execute all subtask agents in parallel."""
    from app.agents.orchestrator.service import AGENT_REGISTRY

    task_defs = state.get("task_defs", [])
    user_id = state["user_id"]
    memory_context = state.get("memory_context", {})
    db = _db_var.get()

    if not task_defs:
        return {"agent_results": {}}

    results: dict[str, AgentResult] = {}
    coros = []

    for td_dict in task_defs:
        agent_type = td_dict.get("agent", "")
        params = td_dict.get("params", {})
        params["memory_context"] = memory_context
        params["action"] = params.get("action", td_dict.get("action", "run"))

        factory = AGENT_REGISTRY.get(agent_type)
        if factory:
            agent = factory(db, user_id)
            coros.append(_run_class_agent(agent_type, agent, params))

    if coros:
        agent_results_list = await asyncio.gather(*coros, return_exceptions=True)
        for item in agent_results_list:
            if isinstance(item, Exception):
                logger.warning("Agent dispatch raised exception: %s", item)
                continue
            if isinstance(item, AgentResult):
                results[item.agent_type] = item
            elif isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, AgentResult):
                        results[k] = v
                    elif isinstance(v, dict):
                        results[k] = AgentResult(
                            agent_type=k,
                            status=AgentStatus.COMPLETED if "error" not in v else AgentStatus.FAILED,
                            output=v if "error" not in v else None,
                            error=v.get("error") if "error" in v else None,
                        )

    logger.info("dispatch_agents: %d agent(s) completed", len(results))
    return {"agent_results": results}


async def _run_class_agent(agent_type: str, agent: Any, params: dict) -> AgentResult:
    """Execute a single agent with retry and timeout."""
    from app.agents.orchestrator.service import _run_with_retry

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


async def _reflect(state: PlannerState) -> dict:
    """
    Score all agent outputs on the 5-dimension rubric.

    This is a pure scoring node — no inline regeneration.
    The conditional edge handles routing back to ``dispatch_agents``
    for retry of low-scoring agents.
    """
    goal = state["goal"]
    agent_results = state.get("agent_results", {})
    profile_skills = state.get("profile_skills", [])
    iteration = state.get("reflection_iterations", 0)

    reflection_scores: dict[str, dict] = {}
    for agent_key, agent_res in agent_results.items():
        result_dict = (
            agent_res.output or {"error": agent_res.error}
            if agent_res.error
            else (agent_res.output or {})
        )
        reflection_scores[agent_key] = await _score_agent_output(
            agent_key, result_dict, goal, profile_skills,
        )

    new_iteration = iteration + 1

    low_scorers = [
        k for k, v in reflection_scores.items()
        if isinstance(v, dict) and v.get("total", 0) < QUALITY_THRESHOLD
    ]

    if low_scorers and new_iteration < MAX_REFLECTION_ITERATIONS:
        logger.info(
            "reflect (iter %d): %d agent(s) below threshold — will retry",
            iteration + 1,
            len(low_scorers),
        )

    return {
        "reflection_scores": reflection_scores,
        "reflection_iterations": new_iteration,
    }


async def _format_output(state: PlannerState) -> dict:
    """Build the final output dict from agent results."""
    goal = state["goal"]
    agent_results = state.get("agent_results", {})
    reflection_scores = state.get("reflection_scores", {})

    flat: dict[str, dict] = {}
    detail: dict[str, dict] = {}
    for agent_type, result in agent_results.items():
        flat[agent_type] = {
            "status": result.status,
            "message": (
                (result.output or {}).get("message", str(result.output)[:200])
                if result.output
                else result.error
            ),
            "duration_ms": result.duration_ms,
        }
        if result.output and result.status == AgentStatus.COMPLETED:
            detail[agent_type] = result.output

    final_output = {
        "results": flat,
        "reflection_scores": reflection_scores,
        "detail": detail,
    }

    return {"final_output": final_output}


# ── Conditional Edge ────────────────────────────────────────


def _should_regenerate(state: PlannerState) -> str:
    """Decide whether to retry low-scoring agents or finalize."""
    agent_results = state.get("agent_results", {})
    reflection_scores = state.get("reflection_scores", {})
    iteration = state.get("reflection_iterations", 0)

    if iteration >= MAX_REFLECTION_ITERATIONS or not agent_results:
        return "format_output"

    low_scorers = [
        k for k, v in reflection_scores.items()
        if isinstance(v, dict) and v.get("total", 0) < QUALITY_THRESHOLD
    ]

    if low_scorers:
        return "dispatch_agents"

    return "format_output"


# ── Graph Singleton ─────────────────────────────────────────
# The graph structure (nodes + edges) is identical across all runs.
# Only the DB session changes — it's passed via state["_db"] instead
# of closures, so we build once and reuse.

_graph = None
_graph_lock = asyncio.Lock()


def _build_graph() -> Any:
    """Build the LangGraph StateGraph (once, synchronously)."""
    builder = StateGraph(PlannerState)

    builder.add_node("load_context", _load_context)
    builder.add_node("decompose_goal", _decompose_goal)
    builder.add_node("filter_tasks", _filter_tasks)
    builder.add_node("dispatch_agents", _dispatch_agents)
    builder.add_node("reflect", _reflect)
    builder.add_node("format_output", _format_output)

    builder.set_entry_point("load_context")
    builder.add_edge("load_context", "decompose_goal")
    builder.add_edge("decompose_goal", "filter_tasks")
    builder.add_edge("filter_tasks", "dispatch_agents")
    builder.add_edge("dispatch_agents", "reflect")

    builder.add_conditional_edges(
        "reflect",
        _should_regenerate,
        {
            "dispatch_agents": "dispatch_agents",
            "format_output": "format_output",
        },
    )

    builder.add_edge("format_output", END)

    return builder


async def _get_compiled_graph():
    """Return the compiled graph, building and caching it on first call."""
    global _graph

    if _graph is not None:
        return _graph

    async with _graph_lock:
        if _graph is not None:
            return _graph

        builder = _build_graph()

        from app.checkpointer import get_checkpointer
        checkpointer = await get_checkpointer()

        _graph = builder.compile(checkpointer=checkpointer)
        return _graph


# ── LangSmith Trace URL ────────────────────────────────────


def _get_langsmith_trace_url(run_id: str) -> str | None:
    """Construct the LangSmith trace URL for a completed run.

    Uses the ``langsmith`` SDK when available, falling back to a
    best-effort URL from the project name.
    """
    import os

    project = os.environ.get("LANGCHAIN_PROJECT", "agentforge-career-os")

    # Try the official SDK first — it handles org/project resolution.
    try:
        from langsmith import Client

        client = Client()
        run = client.read_run(run_id)
        if run.url:
            return run.url
    except Exception as exc:
        logger.debug("LangSmith SDK trace URL lookup failed: %s", exc)  # SDK unavailable or run not found yet

    # Fallback: construct a direct link using the project name.
    # NOTE: This URL may 404 if the org slug isn't 'default' or LangSmith
    # didn't use our run_id. Return None to avoid broken links.
    return None


# ── Convenience Runner ──────────────────────────────────────


async def run_planner_graph(
    db: AsyncSession,
    user_id: str,
    goal: str,
) -> dict:
    """
    Run the full LangGraph planner pipeline with a single call.

    This is the primary entry point for planner execution.
    Returns a dict matching the ``final_output`` schema:

    .. code-block:: python

        {
            "results": {"agent_type": {"status": "...", "message": "...", "duration_ms": ...}},
            "reflection_scores": {"agent_type": {"accuracy": 8, ..., "total": 34}},
            "detail": {"agent_type": {"items": [...], ...}},
        }
    """
    graph = await _get_compiled_graph()
    run_id = str(uuid.uuid4())
    config = {
        "run_id": run_id,
        "configurable": {"thread_id": f"planner:{user_id}:{run_id}"},
        "tags": ["planner", "agentforge"],
        "metadata": {"user_id": user_id, "run_id": run_id},
    }

    token = _db_var.set(db)
    try:
        initial_state: PlannerState = {
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

        final_state = await graph.ainvoke(initial_state, config)
        output = final_state.get("final_output", {})

        # Attach LangSmith trace URL so the frontend can link to run details
        trace_url = _get_langsmith_trace_url(run_id)
        if trace_url:
            output["trace_url"] = trace_url
        output["run_id"] = run_id

        return output
    finally:
        _db_var.reset(token)
