"""Networking Agent — outreach message generation."""

import logging

from app.agents.base import BaseAgent
from app.agents.networking_agent.handlers import generate_outreach

logger = logging.getLogger("agentforge.agents.networking")


class NetworkingAgent(BaseAgent):
    """Handles networking outreach message generation."""

    agent_type = "networking"

    async def execute(self, params: dict) -> dict:
        return await generate_outreach(self.user_id, params, self.db)
