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
    AgentTask,
    AgentType,
    TaskStatus,
    PlannerGoal,
    Opportunity,
)
from app.agents.planner import decompose_goal_with_llm, format_planner_response
from app.agents.internship_agent import discover_internships
from app.agents.job_agent import discover_jobs
from app.agents.research_agent import conduct_research
from app.agents.assistant_agent import (
    tailor_resume,
    prepare_interview,
    generate_outreach,
    run_daily_scan,
    get_career_guidance,
)
from app.utils.demo_data import generate_demo_opportunities
from app.utils.location import parse_location
from app.utils.industry import detect_industry
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService
from app.services.notification_service import create_notification

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
        os.environ.setdefault(
            "LANGCHAIN_PROJECT", settings.app_name.replace(" ", "-").lower()
        )
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        logger.info(
            "LangSmith tracing enabled (project=%s)", os.environ["LANGCHAIN_PROJECT"]
        )


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Agent Map (shared across nodes) ────────────────────────

AGENT_TIMEOUT = 120  # seconds — per-agent timeout for asyncio.gather()
AGENT_MAX_RETRIES = 2  # retry attempts with exponential backoff

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
    reflection_scores: dict[str, dict]
    reflection_iterations: int
    needs_regeneration: bool


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
        await db.commit()

    return {
        "tasks": task_list,
        "planner_goal_id": str(planner_goal.id),
        "planner_task_id": planner_task_id,
        "error": None,
    }


# ─── Retry / Timeout Helpers ─────────────────────────────────


async def _execute_with_retry(
    agent_str: str,
    user_id: str,
    params: dict,
    planner_goal_id: str | None,
) -> dict:
    """
    Execute a single agent with exponential backoff retry.

    Retry schedule: attempt 0 fails -> 1s wait -> attempt 1 fails -> 2s wait -> attempt 2.
    Each attempt is individually timed out via asyncio.wait_for.
    """
    last_error: Exception | None = None
    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            coro = _execute_single_agent_inner(
                agent_str, user_id, params, planner_goal_id
            )
            return await asyncio.wait_for(coro, timeout=AGENT_TIMEOUT)
        except asyncio.TimeoutError:
            last_error = TimeoutError(
                f"Agent {agent_str} timed out after {AGENT_TIMEOUT}s"
            )
            logger.warning(
                "Agent %s timed out (attempt %d/%d)",
                agent_str,
                attempt + 1,
                AGENT_MAX_RETRIES + 1,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "Agent %s failed (attempt %d/%d): %s",
                agent_str,
                attempt + 1,
                AGENT_MAX_RETRIES + 1,
                e,
            )

        if attempt < AGENT_MAX_RETRIES:
            wait = 2**attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait)

    return {agent_str: {"error": str(last_error)}}


# ─── Parallel Agent Dispatch Helpers ────────────────────────


async def _execute_single_agent_inner(
    agent_str: str,
    user_id: str,
    params: dict,
    planner_goal_id: str | None,
) -> dict:
    """
    Execute a single specialist agent in its own DB session.
    This enables true parallel execution via asyncio.gather().
    """
    try:
        agent_type = AgentType(agent_str)
    except ValueError:
        agent_type = AgentType.monitor

    handler = AGENT_HANDLERS.get(agent_type)
    specialist_task_id = gen_id()

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

            await create_notification(
                db,
                user_id,
                title=f"{agent_type.value.title()} task completed",
                body=f"Your {agent_type.value} task finished successfully.",
                type="success",
            )

            await db.commit()
            return {agent_str: agent_result}

        except Exception as e:
            logger.warning("Agent %s failed: %s", agent_str, e)
            spec_task.status = TaskStatus.failed
            spec_task.error = str(e)
            spec_task.completed_at = datetime.now(timezone.utc)

            await create_notification(
                db,
                user_id,
                title=f"{agent_type.value.title()} task failed",
                body=str(e)[:200],
                type="error",
            )

            return {agent_str: {"error": str(e)}}


# ─── Dynamic Agent Routing ──────────────────────────────────


def _filter_tasks_by_context(tasks: list[dict], profile: dict) -> list[dict]:
    """
    Dynamically filter agent tasks based on user profile context.

    - Skip internship agent if user's role types explicitly exclude internships.
    - Skip job agent if user only wants internships.
    - Skip research agent with default params if the user has no target companies.
    """
    role_types = profile.get("role_types", [])
    target_locations = profile.get("target_locations", [])
    career_goal = profile.get("career_goal", "").lower()

    filtered: list[dict] = []
    for task in tasks:
        agent = task.get("agent", "")

        # Skip internship if role types exclude internship
        if agent == "internship" and role_types:
            if all("intern" not in rt.lower() for rt in role_types):
                logger.info(
                    "Dynamic routing: skipping internship agent (role types: %s)",
                    role_types,
                )
                continue

        # Skip job agent if user only wants internships
        if agent == "job" and role_types:
            if all(
                "full" not in rt.lower() and "job" not in rt.lower()
                for rt in role_types
            ):
                if any("intern" in rt.lower() for rt in role_types):
                    logger.info(
                        "Dynamic routing: skipping job agent (role types: %s)",
                        role_types,
                    )
                    continue

        # Skip research agent if no query and no target locations
        if agent == "research":
            query = task.get("params", {}).get("query", "")
            if not query and not target_locations:
                logger.info(
                    "Dynamic routing: skipping research agent (no query or target location)"
                )
                continue

        # Enrich task with user context for downstream agents
        params = task.get("params", {})
        if career_goal and "career_goal" not in params:
            params["career_goal"] = career_goal
        task["params"] = params

        filtered.append(task)

    return filtered


async def dispatch_all_agents_node(state: PlannerGraphState) -> dict:
    """
    Graph node: dispatch all specialist agents in parallel using asyncio.gather().

    Features:
      - Retry with exponential backoff per agent
      - Timeout per agent via asyncio.wait_for
      - Priority-based task ordering
      - Dynamic routing: skips irrelevant agents based on user profile
    """
    user_id = state["user_id"]
    tasks = state.get("tasks", [])
    profile = state.get("profile", {})
    planner_goal_id = state.get("planner_goal_id")
    memory_context = state.get("memory_context", {})

    if not tasks:
        return {"results": {}}

    # 1. Dynamic routing — filter irrelevant tasks based on user context
    tasks = _filter_tasks_by_context(tasks, profile)

    if not tasks:
        logger.info("All tasks filtered out by dynamic routing")
        return {"results": {}}

    # 2. Priority sort — highest priority first (lower number = higher priority)
    tasks.sort(key=lambda t: t.get("priority", 5))

    logger.info(
        "Dispatching %d specialist agents in parallel (with retry+timeout)",
        len(tasks),
    )

    # 3. Create retry-wrapped coroutines for all agents
    coros = []
    for task_def in tasks:
        agent_str = task_def.get("agent", "monitor")
        params = task_def.get("params", {})
        params["memory_context"] = memory_context
        coro = _execute_with_retry(agent_str, user_id, params, planner_goal_id)
        coros.append(coro)

    # 4. Execute all agents in parallel — return_exceptions=True so one
    #    agent crash doesn't discard results from all other agents
    results_list = await asyncio.gather(*coros, return_exceptions=True)

    # 5. Merge individual results into a single dict, handling exceptions
    merged_results: dict[str, Any] = {}
    for i, result_item in enumerate(results_list):
        if isinstance(result_item, Exception):
            logger.warning("Agent execution raised exception: %s", result_item)
            merged_results[f"error_{i}"] = {"error": str(result_item)}
        else:
            merged_results.update(result_item)

    logger.info(
        "Parallel dispatch complete: %d succeeded, %d failed",
        sum(
            1
            for v in merged_results.values()
            if isinstance(v, dict) and "error" not in v
        ),
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

    from app.utils.work_mode import infer_work_type

    items = []
    for r in raw_results[:10]:
        loc_raw = r.get("location")
        parsed = parse_location(loc_raw)
        industry = detect_industry(
            title=r.get("title", ""),
            company=r.get("company", ""),
            description=r.get("description", ""),
        )

        remote = r.get("remote", False)
        work_type = r.get("work_type") or infer_work_type(
            remote, r.get("title"), r.get("description"), loc_raw
        )

        opp = Opportunity(
            user_id=user_id,
            title=r.get("title", "Untitled"),
            company=r.get("company", "Unknown"),
            location=loc_raw,
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"],
            industry=industry,
            remote=remote,
            work_type=work_type,
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
    agent_type: AgentType,
    user_id: str,
    params: dict,
    db: AsyncSession,
    memory_context: dict | None = None,
) -> dict:
    """
    Dispatch a single specialist agent task and return its result.
    Used by the streaming chat endpoint (chat.py) for sequential dispatch.
    """
    if memory_context:
        params["memory_context"] = memory_context
    handler = AGENT_HANDLERS.get(agent_type)
    if handler:
        return await handler(user_id, params, db)
    return await _fallback_search(user_id, params, db, agent_type)


# ─── Reflection Scoring ─────────────────────────────────────

REFLECTION_RUBRIC = {
    "accuracy": "No hallucinations, sources verifiable",
    "specificity": "Tailored to user, not generic",
    "actionability": "Contains next steps the user can actually take",
    "tone_match": "Matches the user's communication preferences",
    "format_quality": "Correct structure, no broken JSON, readable",
}


async def _score_agent_output(
    agent_type: str,
    result: dict,
    goal: str,
    profile: dict,
) -> dict:
    """Score an agent's output against the reflection rubric (0-10 each)."""
    scores = {}
    total = 0

    if not result or "error" in result:
        for dim in REFLECTION_RUBRIC:
            scores[dim] = 0
        scores["total"] = 0
        scores["feedback"] = "Agent returned error or empty result"
        return scores

    # Heuristic scoring (always available, no LLM needed)
    result_str = str(result)
    items = result.get("items", [])
    message = result.get("message", "")

    # Accuracy: penalize generic error messages, reward structured data
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

    # Specificity: check for skill references, company names, concrete details
    profile_skills = profile.get("skills", [])
    specificity = 4
    for skill in profile_skills:
        if isinstance(skill, str) and skill.lower() in result_str.lower():
            specificity += 1
    if message and len(message) > 30:
        specificity += 2
    if items:
        specificity += 2
    if goal.lower() in result_str.lower():
        specificity += 1
    scores["specificity"] = min(10, specificity)

    # Actionability: contains next steps or concrete items
    actionability = 5
    if items:
        actionability = 8
    if result.get("action_items"):
        actionability = min(10, actionability + 2)
    if result.get("next_steps"):
        actionability = min(10, actionability + 2)
    if result.get("tips"):
        actionability = min(10, actionability + 1)
    if result.get("suggestions"):
        actionability = min(10, actionability + 1)
    scores["actionability"] = actionability

    # Tone match: check for professional tone indicators
    tone_markers = [
        "recommend",
        "suggest",
        "consider",
        "based on",
        "opportunity",
        "skill",
    ]
    tone = 6
    for marker in tone_markers:
        if marker in result_str.lower():
            tone += 1
    if any(c.isupper() for c in message[:3] if c.isalpha()):
        tone += 1
    scores["tone_match"] = min(10, tone)

    # Format quality: check structure
    fmt = 4
    if isinstance(result, dict):
        fmt = 6
        if "message" in result:
            fmt += 1
        if "items" in result or "questions" in result or "guidance" in result:
            fmt += 1
        if isinstance(result.get("items"), list) or isinstance(
            result.get("questions"), list
        ):
            fmt += 2
    scores["format_quality"] = min(10, fmt)

    total = sum(v for k, v in scores.items() if k != "total")
    scores["total"] = total
    scores["feedback"] = _generate_reflection_feedback(scores, agent_type, result)
    return scores


def _generate_reflection_feedback(
    scores: dict,
    agent_type: str,
    result: dict,
) -> str:
    """Generate human-readable reflection feedback."""
    weaknesses = []
    for dim, score in scores.items():
        if dim == "total" or dim == "feedback":
            continue
        if score < 5:
            weaknesses.append(f"{dim} is low ({score}/10)")
    if weaknesses:
        return f"{agent_type}: " + "; ".join(weaknesses)
    return f"{agent_type}: Output quality acceptable"


async def reflect_on_results_node(state: PlannerGraphState) -> dict:
    """
    Graph node: score all agent results against the reflection rubric.

    Identifies underperforming agents and triggers regeneration
    if scores fall below the threshold.
    """
    results = state.get("results", {})
    goal = state.get("goal", "")
    profile = state.get("profile", {})
    iteration = state.get("reflection_iterations", 0)

    reflection_scores = {}
    needs_regeneration = False

    for agent_type, result in results.items():
        scores = await _score_agent_output(agent_type, result, goal, profile)
        reflection_scores[agent_type] = scores

        if scores["total"] < 35 and iteration < 2:
            needs_regeneration = True
            logger.info(
                "Reflection: %s scored %d/50 (iteration %d) — will regenerate",
                agent_type,
                scores["total"],
                iteration,
            )

    passed = sum(1 for s in reflection_scores.values() if s["total"] >= 35)
    total_agents = len(reflection_scores)
    logger.info(
        "Reflection complete: %d/%d agents passed (iteration %d)",
        passed,
        total_agents,
        iteration,
    )

    return {
        "reflection_scores": reflection_scores,
        "needs_regeneration": needs_regeneration,
        "reflection_iterations": iteration + 1,
    }


def should_regenerate(state: PlannerGraphState) -> str:
    """Conditional edge: regenerate or proceed to final response."""
    if state.get("needs_regeneration") and state.get("reflection_iterations", 0) < 2:
        return "dispatch_all_agents"
    return "generate_final_response"


# ─── Node: Generate Final Response ──────────────────────────


async def generate_final_response_node(state: PlannerGraphState) -> dict:
    """
    Graph node: produce the final planner response and update DB records.
    """
    user_id = state["user_id"]
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

                await create_notification(
                    db,
                    user_id,
                    title="Goal completed",
                    body="Your goal has been processed.",
                    type="success",
                )

        await db.commit()

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
    builder.add_node("reflect_on_results", reflect_on_results_node)
    builder.add_node("generate_final_response", generate_final_response_node)

    builder.add_edge(START, "decompose_goal")
    builder.add_edge("decompose_goal", "dispatch_all_agents")
    builder.add_edge("dispatch_all_agents", "reflect_on_results")
    builder.add_conditional_edges(
        "reflect_on_results",
        should_regenerate,
        {
            "dispatch_all_agents": "dispatch_all_agents",
            "generate_final_response": "generate_final_response",
        },
    )
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
        "reflection_scores": {},
        "reflection_iterations": 0,
        "needs_regeneration": False,
    }

    # Invoke the LangGraph (lazy-compiled singleton)
    graph = get_planner_graph()
    final_state = await graph.ainvoke(initial_state)

    # Return the planner task ID so callers can poll status
    return final_state.get("planner_task_id") or gen_id()


# ─── Direct API Entry Points ────────────────────────────────


async def run_opportunity_scan(user_id: str, query: Optional[str] = None) -> str:
    """Run the opportunity monitor to scan for new openings."""
    task_id = gen_id()
    params = {"action": "scan"}
    if query:
        params["search_query"] = query

    async with async_session_factory() as db:
        task = AgentTask(
            id=task_id,
            user_id=user_id,
            agent_type=AgentType.monitor,
            input=params,
            status=TaskStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()

        try:
            result = await run_daily_scan(user_id, params, db)

            task.status = TaskStatus.completed
            task.output = result
            task.completed_at = datetime.now(timezone.utc)
            await db.flush()

            await create_notification(
                db,
                user_id,
                title="Opportunity scan complete",
                body="New opportunities may be available. Check your matches!",
                type="info",
            )

        except Exception as e:
            task.status = TaskStatus.failed
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await db.flush()

            await create_notification(
                db,
                user_id,
                title="Opportunity scan failed",
                body=str(e)[:200],
                type="error",
            )
            await db.rollback()
            return task_id

        await db.commit()
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
            status=TaskStatus.running,
            started_at=datetime.now(timezone.utc),
        )

        if app:
            opp_result = await db.execute(
                select(Opportunity).where(Opportunity.id == app.opportunity_id)
            )
            opp = opp_result.scalar_one_or_none()
            result = await tailor_resume(
                user_id,
                {
                    "role_type": opp.type.lower() if opp else "internship",
                    "target_company": opp.company if opp else None,
                    "skills": opp.skills_required if opp else [],
                    "application_id": application_id,
                },
                db,
            )
            task.output = result
        else:
            task.output = {"error": "Application not found"}

        task.status = TaskStatus.completed
        task.completed_at = datetime.now(timezone.utc)
        db.add(task)
        await db.commit()

    return task_id
