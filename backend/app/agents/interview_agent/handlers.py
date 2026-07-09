"""Interview Agent handlers — interview preparation and answer review."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import strip_json_fences
from app.agents.constants import (
    COLLECTION_MEMORY_NOTES,
    DEFAULT_ROLE_TYPE,
    LLM_PROVIDER_INTERVIEW,
    LLM_TEMPERATURE_CREATIVE,
    LLM_TEMPERATURE_PRECISE,
    MAX_INTERVIEW_PREP_TIPS,
    MAX_INTERVIEW_SKILLS,
    MEMORY_KEY_INTERVIEW,
    MEMORY_WEIGHT_MEDIUM,
)
from app.agents.enrichment import build_enrichment_context
from app.agents.prompts.interview import prepare_interview_prompt, review_answer_prompt
from app.memory.memory_layer import AgentMemory
from app.services.memory_service import MemoryService
from app.services.model_manager import get_completion_llm
from app.services.profile_service import ProfileService
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.agents.interview.handlers")


async def prepare_interview(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Generate interview preparation materials based on user's profile."""
    role_type = params.get("role_type", DEFAULT_ROLE_TYPE)
    skills = params.get("skills", [])
    company = params.get("company")

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    ctx = await build_enrichment_context(db, user_id, all_skills)

    llm = get_completion_llm(temperature=LLM_TEMPERATURE_CREATIVE, preferred_provider=LLM_PROVIDER_INTERVIEW)
    questions = None
    prep_tips = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = prepare_interview_prompt(all_skills, role_type, company, ctx.github_context, ctx.portfolio_context)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(strip_json_fences(response.content))

            if isinstance(parsed, dict) and "questions" in parsed and isinstance(parsed["questions"], list):
                questions = parsed["questions"]
            if isinstance(parsed, dict) and "prep_tips" in parsed and isinstance(parsed["prep_tips"], list):
                prep_tips = parsed["prep_tips"][:MAX_INTERVIEW_PREP_TIPS]
        except Exception as e:
            logger.warning("LLM prepare_interview failed, falling back to template: %s", e)

    if questions is None:
        questions = _fallback_interview_questions(all_skills, ctx)

    if prep_tips is None:
        prep_tips = _fallback_interview_tips(all_skills, company, ctx)

    try:
        await memory_service.set_memory(
            user_id,
            MEMORY_KEY_INTERVIEW,
            {
                "role_type": role_type,
                "skills": all_skills,
                "company": company,
                "prepared_at": datetime.now(UTC).isoformat(),
            },
            weight=MEMORY_WEIGHT_MEDIUM,
        )
    except Exception as e:
        logger.debug("Failed to store interview prep memory: %s", e)

    result = {
        "questions": questions,
        "total_questions": len(questions),
        "prep_tips": prep_tips,
        "focus_areas": all_skills[:3] + ["System Design Fundamentals", "Behavioral Storytelling"],
        "message": f"Generated {len(questions)} interview questions for preparation",
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection=COLLECTION_MEMORY_NOTES,
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "interview",
                "key": params.get("role_type", ""),
                "timestamp": str(datetime.now(UTC)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


async def review_interview_answer(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Review a user's interview answer and provide structured feedback."""
    question = params.get("question", "")
    answer = params.get("answer", "")
    company = params.get("company")
    role = params.get("role")

    llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PROVIDER_INTERVIEW)

    if not llm:
        return {
            "feedback": "AI review is unavailable. Your answer was recorded.",
            "score": None,
            "strengths": [],
            "improvements": [],
        }

    try:
        from langchain_core.messages import HumanMessage

        prompt = review_answer_prompt(question, answer, company, role)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        parsed = json.loads(strip_json_fences(response.content))

        return {
            "feedback": parsed.get("feedback", "Your answer was reviewed."),
            "score": parsed.get("score"),
            "strengths": parsed.get("strengths", []),
            "improvements": parsed.get("improvements", []),
        }
    except Exception as e:
        logger.warning("LLM review_interview_answer failed: %s", e)
        return {
            "feedback": "Could not generate AI feedback at this time.",
            "score": None,
            "strengths": [],
            "improvements": [],
        }


# ── Fallback Templates ──────────────────────────────────────


def _fallback_interview_questions(all_skills: list[str], ctx) -> list[dict]:
    """Generate fallback interview questions when LLM is unavailable."""
    _project_names = ctx.pf_projects[:3] if ctx.pf_projects else []
    _project_ref = f"like your portfolio project '{_project_names[0]}'" if _project_names else ""

    questions = []
    for idx, skill in enumerate(all_skills[:MAX_INTERVIEW_SKILLS]):
        project_suffix = f" — specifically in {_project_ref}" if _project_ref and idx < 2 else ""
        questions.append(
            {
                "skill": skill,
                "question": f"Describe your experience with {skill} and a project where you used it effectively.{project_suffix}",
                "type": "behavioral",
                "tips": f"Use STAR format. Highlight a specific project where {skill} was critical.",
            }
        )
        questions.append(
            {
                "skill": skill,
                "question": f"What are the trade-offs and challenges when working with {skill} at scale?",
                "type": "technical",
                "tips": "Discuss performance, maintainability, and real-world constraints.",
            }
        )
    questions.extend(
        [
            {
                "skill": "general",
                "question": "Tell me about yourself and your background.",
                "type": "behavioral",
                "tips": "Structure it: present → past → future. Keep it under 2 minutes.",
            },
            {
                "skill": "general",
                "question": "Why are you interested in this role/company?",
                "type": "behavioral",
                "tips": "Show you've done your research. Mention specific products or initiatives.",
            },
            {
                "skill": "general",
                "question": "Describe a time you resolved a conflict or disagreement in a team.",
                "type": "behavioral",
                "tips": "Focus on communication and compromise. Show growth.",
            },
        ]
    )
    return questions


def _fallback_interview_tips(all_skills: list[str], company: str | None, ctx) -> list[str]:
    """Generate fallback prep tips when LLM is unavailable."""
    tips = [
        f"Practice {len(all_skills[:3])} technical deep-dives on {', '.join(all_skills[:3])}",
        "Prepare 3 STAR stories highlighting leadership and impact",
        f"Research {company or 'the company'} recent news and product launches",
        "Prepare 3-4 thoughtful questions to ask the interviewer",
        "Do a mock interview with a friend or use the Interview Copilot",
    ]
    if ctx.pf_projects:
        tips.append(f"Walk through your portfolio projects: {', '.join(ctx.pf_projects[:3])}")
    if ctx.portfolio_context or ctx.github_context:
        tips.append("Be ready to dive into specific technical decisions from your GitHub/portfolio projects")
    return tips
