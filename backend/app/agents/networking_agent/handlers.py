"""Networking Agent handlers — outreach message generation."""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.model_manager import get_completion_llm
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding
from app.agents.enrichment import build_enrichment_context
from app.agents.base import strip_json_fences
from app.agents.constants import (
    LLM_TEMPERATURE_CREATIVE,
    LLM_PREFERRED_PROVIDER,
    MEMORY_WEIGHT_LOW,
    MEMORY_KEY_NETWORKING,
    COLLECTION_MEMORY_NOTES,
    MAX_NETWORKING_BEST_PRACTICES,
    MAX_NETWORKING_PROJECTS,
)
from app.agents.prompts.networking import outreach_prompt

logger = logging.getLogger("agentforge.agents.networking.handlers")


async def generate_outreach(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Generate outreach messages for networking."""
    target_companies = params.get("target_companies", [])
    role = params.get("role", "")
    skills = params.get("skills", [])

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    ctx = await build_enrichment_context(db, user_id, all_skills)

    llm = get_completion_llm(temperature=LLM_TEMPERATURE_CREATIVE, preferred_provider=LLM_PREFERRED_PROVIDER)
    templates = None
    best_practices = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = outreach_prompt(all_skills, role, target_companies, ctx.github_context, ctx.portfolio_context)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(strip_json_fences(response.content))

            if isinstance(parsed, dict) and "templates" in parsed and isinstance(parsed["templates"], list):
                templates = parsed["templates"]
            if isinstance(parsed, dict) and "best_practices" in parsed and isinstance(parsed["best_practices"], list):
                best_practices = parsed["best_practices"][:MAX_NETWORKING_BEST_PRACTICES]
        except Exception as e:
            logger.warning("LLM generate_outreach failed, falling back to template: %s", e)

    if templates is None:
        templates = _fallback_outreach_templates(all_skills, role, target_companies, ctx)

    if best_practices is None:
        best_practices = ["Personalize each message with specific details about the recipient", "Keep the first message under 150 words", "Include a clear, low-friction ask (e.g., 15-min chat)", "Follow up after 5-7 days if you don't hear back", "Connect on LinkedIn before sending a message"]

    try:
        await memory_service.set_memory(user_id, MEMORY_KEY_NETWORKING, {
            "target_companies": target_companies,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, weight=MEMORY_WEIGHT_LOW)
    except Exception as e:
        logger.debug("Failed to store networking memory: %s", e)

    result = {"templates": templates, "message": f"Generated {len(templates)} outreach templates", "best_practices": best_practices}

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(collection=COLLECTION_MEMORY_NOTES, text=result["message"], vector=vector, metadata={
            "agent_type": "outreach", "key": params.get("role", ""),
            "timestamp": str(datetime.now(timezone.utc)),
        })
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


# ── Fallback Templates ──────────────────────────────────────


def _fallback_outreach_templates(all_skills: list[str], role: str, target_companies: list[str], ctx) -> list[dict]:
    """Generate fallback outreach templates when LLM is unavailable."""
    project_bullets = ""
    if ctx.pf_projects:
        project_bullets = "My recent projects include:\n"
        for proj in ctx.pf_projects[:MAX_NETWORKING_PROJECTS]:
            project_bullets += f"- {proj}\n"
        project_bullets += "\n"

    templates = []
    for company in target_companies or ["target companies"]:
        templates.append({
            "type": "cold_email",
            "subject": f"Interested in {role} opportunities at {company}",
            "message": f"Hi [Name],\n\nI'm reaching out because I'm very interested in {company} and would love to learn more about your work. I have experience in {', '.join(all_skills[:3])} and I'm exploring {role} opportunities.\n\n{project_bullets}Would you be open to a 15-minute chat?\n\nBest,\n[Your Name]",
        })
        templates.append({
            "type": "linkedin_message", "subject": "",
            "message": f"Hi [Name]! I'm exploring {role} opportunities at {company} and was impressed by your background in {', '.join(all_skills[:2])}. {'I have projects in ' + ', '.join(ctx.pf_projects[:2]) + '. ' if ctx.pf_projects else ''}Would love to connect and learn more about your journey!",
        })
    return templates
