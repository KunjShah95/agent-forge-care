"""Guidance Agent handlers — career guidance and planning."""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.constants import COLLECTION_MEMORY_NOTES
from app.memory.memory_layer import AgentMemory
from app.services.profile_service import ProfileService
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.agents.guidance.handlers")


async def get_career_guidance(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Provide personalized career guidance."""
    profile_service = ProfileService(db)
    agent_memory = AgentMemory(user_id)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)

    guidance = {
        "profile_summary": {
            "name": profile.school or "Student",
            "skills": profile_skills,
            "target_locations": profile.target_locations or ["Remote"],
            "career_goal": profile.career_goal or "Not yet defined",
        },
        "next_steps": [
            f"Apply to {len(profile_skills)} matching opportunities",
            "Update your resume with latest projects",
            "Set up daily monitor alerts for new openings",
            "Connect with 5 recruiters on LinkedIn this week",
        ],
        "tips": [
            "Tailor each application — generic applications have lower conversion",
            "Build a portfolio project showcasing your strongest skills",
            "Join relevant communities (Discord, Slack, meetups) in your target domain",
        ],
    }

    if profile_skills:
        query_vector = await get_text_embedding(f"career guidance for skills: {', '.join(profile_skills)}")
        relevant_context = agent_memory.get_relevant_context(query_vector, limit=3)
        guidance["memory_context"] = relevant_context

    result = {"guidance": guidance, "message": "Career guidance generated based on your profile and market conditions"}

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection=COLLECTION_MEMORY_NOTES,
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "guidance",
                "key": params.get("query", ""),
                "timestamp": str(datetime.now(UTC)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result
