"""Guidance Agent — career guidance and planning."""

import logging

from app.agents.base import BaseAgent
from app.agents.guidance_agent.handlers import get_career_guidance

logger = logging.getLogger("agentforge.agents.guidance")


class GuidanceAgent(BaseAgent):
    """Handles career guidance and planning."""

    agent_type = "guidance"

    async def execute(self, params: dict) -> dict:
        return await get_career_guidance(self.user_id, params, self.db)
