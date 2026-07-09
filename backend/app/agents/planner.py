"""
Planner Agent — the central orchestrator of the AgentForge system.

The planner receives a user goal, decomposes it into sub-tasks
using an LLM (when available), dispatches each to the appropriate
specialist agent, and collects results.
"""

import json
import logging
from typing import TypedDict

from app.services.model_manager import get_completion_llm

logger = logging.getLogger("agentforge.planner")


class Task(TypedDict):
    """A single task unit for a specialist agent."""

    agent: str  # internship, job, research, resume, interview, networking, monitor
    action: str
    params: dict
    priority: int


# ─── LLM-based Goal Decomposition ──────────────────────────


def _build_decomposition_prompt(goal: str, profile: dict, memory_context: dict) -> str:
    """Build a structured prompt for the LLM to decompose a career goal."""
    skills = ", ".join(profile.get("skills", [])) or "not specified"
    locations = ", ".join(profile.get("target_locations", [])) or "not specified"
    role_types = ", ".join(profile.get("role_types", [])) or "not specified"
    career_goal = profile.get("career_goal", "") or "not specified"

    return f"""You are a career-planning AI that decomposes user goals into executable tasks for a multi-agent system.

SYSTEM CAPABILITIES — available specialist agents:
- internship — searches for internships, fellowships, hackathons
- job — searches for full-time roles, new grad positions
- research — researches companies, interview insights, market intelligence
- resume — tailors resumes, generates cover letters
- interview — generates mock interview questions, prep materials
- networking — drafts outreach messages, networking plans
- monitor — general opportunity scan, broad monitoring

USER PROFILE:
- Skills: {skills}
- Target locations: {locations}
- Role types: {role_types}
- Career goal: {career_goal}

TASK: Decompose the following user goal into a JSON array of task objects.
Each task object must have these keys:
  - "agent": one of the agent names above
  - "action": a clear one-sentence description of what to do
  - "priority": 1 (high), 2 (medium), or 3 (low)
  - "params": an object with contextual parameters for the agent

For the internship and job agents, include params like:
  - "query": search query string derived from the goal
  - "location": specific location if mentioned, otherwise null
  - "skills": relevant skills array
  - "limit": max results (usually 20)

For the research agent, include:
  - "query": the research topic
  - "topics": specific areas to investigate

For the resume agent, include:
  - "role_type": type of role
  - "skills": skills to emphasize
  - "target_companies": companies if mentioned

For the interview agent, include:
  - "role_type": type of role
  - "skills": skills to focus on
  - "question_count": number of questions (usually 10)

For the networking agent, include:
  - "target_companies": companies if mentioned
  - "location": location if mentioned

For the monitor agent, include:
  - "query": general search query
  - "limit": max results

USER GOAL: {goal}

Return ONLY a valid JSON array. No explanations, no markdown formatting, no code blocks.
Example:
[{{"agent": "internship", "action": "Search for AI internships in Ahmedabad", "priority": 1, "params": {{"query": "AI internships in Ahmedabad", "location": "Ahmedabad", "skills": ["Python", "Machine Learning"], "limit": 20}}}}]"""


async def llm_decompose_goal(goal: str, profile: dict, memory_context: dict) -> list[Task] | None:
    """
    Decompose a goal using the best available LLM (multi-provider fallback chain).
    Returns None if LLM is unavailable or fails (caller falls back to keyword method).
    """
    llm = get_completion_llm(temperature=0.3, preferred_provider="openai")
    if not llm:
        logger.debug("LLM decomposition skipped: no LLM provider available")
        return None

    try:
        from langchain_core.messages import HumanMessage

        prompt = _build_decomposition_prompt(goal, profile, memory_context)
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            content = content.rsplit("```", 1)[0]
        if content.startswith("json"):
            content = content[4:].strip()

        tasks_data = json.loads(content)

        if not isinstance(tasks_data, list):
            logger.warning("LLM decomposition returned non-list: %s", type(tasks_data))
            return None

        # Validate and convert to Task TypedDicts
        tasks = []
        for item in tasks_data:
            task = Task(
                agent=item.get("agent", "monitor"),
                action=item.get("action", "General task"),
                params=item.get("params", {}),
                priority=item.get("priority", 2),
            )
            tasks.append(task)

        if not tasks:
            logger.warning("LLM decomposition returned empty list")
            return None

        logger.info("LLM decomposed goal into %d tasks", len(tasks))
        return tasks

    except ImportError as e:
        logger.warning("LangChain not available for LLM decomposition: %s", e)
        return None
    except Exception as e:
        logger.warning("LLM decomposition failed, falling back to keyword method: %s", e)
        return None


# ─── Keyword-based Goal Decomposition (Fallback) ───────────


def _keyword_decompose(goal: str, profile: dict, memory_context: dict) -> list[Task]:
    """Keyword/rules-based decomposition (fallback when no LLM available)."""
    goal_lower = goal.lower()
    tasks = []

    # Detect intent keywords
    has_internship = any(k in goal_lower for k in ["internship", "intern", "summer"])
    has_job = any(k in goal_lower for k in ["job", "full-time", "full time", "role", "position"])
    has_research = any(k in goal_lower for k in ["research", "lab", "professor", "reu"])
    has_resume = any(k in goal_lower for k in ["resume", "cv", "cover letter", "tailor"])
    has_interview = any(k in goal_lower for k in ["interview", "mock", "prepare"])
    has_networking = any(k in goal_lower for k in ["network", "outreach", "connect", "recruiter"])

    # Extract location from goal
    locations = []
    for loc in ["ahmedabad", "remote", "san francisco", "new york", "bay area", "bangalore", "mumbai"]:
        if loc in goal_lower:
            locations.append(loc.title())

    # Extract skills mention
    skill_keywords = [
        "python",
        "typescript",
        "react",
        "machine learning",
        "ai",
        "nlp",
        "pytorch",
        "tensorflow",
        "full-stack",
        "backend",
        "frontend",
    ]
    mentioned_skills = [s for s in skill_keywords if s in goal_lower]

    # Build task list
    if has_internship:
        tasks.append(
            Task(
                agent="internship",
                action="Search for internship opportunities",
                params={
                    "query": goal,
                    "location": locations[0] if locations else None,
                    "skills": mentioned_skills or profile.get("skills", []),
                    "limit": 20,
                },
                priority=1,
            )
        )

    if has_job:
        tasks.append(
            Task(
                agent="job",
                action="Search for job opportunities",
                params={
                    "query": goal,
                    "location": locations[0] if locations else None,
                    "skills": mentioned_skills or profile.get("skills", []),
                    "limit": 20,
                },
                priority=1,
            )
        )

    if has_research:
        tasks.append(
            Task(
                agent="research",
                action="Research companies and interview insights",
                params={
                    "query": goal,
                    "topics": mentioned_skills,
                },
                priority=2,
            )
        )

    if has_resume:
        tasks.append(
            Task(
                agent="resume",
                action="Tailor resume for target roles",
                params={
                    "role_type": "internship" if has_internship else "job",
                    "skills": mentioned_skills,
                    "target_companies": [],
                },
                priority=2,
            )
        )

    if has_interview:
        tasks.append(
            Task(
                agent="interview",
                action="Generate interview preparation materials",
                params={
                    "role_type": "internship" if has_internship else "job",
                    "skills": mentioned_skills,
                    "question_count": 10,
                },
                priority=3,
            )
        )

    if has_networking:
        tasks.append(
            Task(
                agent="networking",
                action="Draft networking outreach messages",
                params={
                    "target_companies": [],
                    "location": locations[0] if locations else None,
                },
                priority=3,
            )
        )

    # If no specific intent detected, do a general scan
    if not tasks:
        tasks.append(
            Task(
                agent="monitor",
                action="General opportunity scan",
                params={
                    "query": goal,
                    "limit": 10,
                },
                priority=1,
            )
        )

    return tasks


async def decompose_goal_with_llm(goal: str, profile: dict, memory_context: dict) -> list[Task]:
    """
    Async entry point: tries LLM decomposition first, falls back to keyword method.
    This is the preferred entry point for the graph nodes and API endpoints.
    """
    # Input validation with graceful fallback
    if not goal or not isinstance(goal, str) or len(goal.strip()) < 3:
        logger.warning("Empty or invalid goal received: %r — returning empty task list", goal)
        return []

    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(memory_context, dict):
        memory_context = {}

    try:
        llm_tasks = await llm_decompose_goal(goal, profile, memory_context)
        if llm_tasks is not None:
            return llm_tasks
        return _keyword_decompose(goal, profile, memory_context)
    except Exception as e:
        logger.error("Goal decomposition failed for goal '%s': %s", goal, str(e))
        raise


# ─── Response Formatting ────────────────────────────────────


def format_planner_response(goal: str, results: dict) -> str:
    """Format the final planner response from all agent results."""
    lines = [f"🎯 **Plan complete for:** {goal}", ""]

    for agent_type, result in results.items():
        if isinstance(result, dict) and result.get("items"):
            lines.append(f"**{agent_type.title()} Agent:** Found {len(result['items'])} matches")
        elif isinstance(result, dict) and result.get("message"):
            lines.append(f"**{agent_type.title()} Agent:** {result['message']}")
        elif isinstance(result, dict) and result.get("error"):
            lines.append(f"**{agent_type.title()} Agent:** ⚠️ {result['error']}")

    if not results:
        lines.append("No results found. Try refining your search or run the monitor for a broader scan.")

    return "\n".join(lines)
