"""Internship Agent — internship discovery and recommendations."""

import logging

from app.agents.base import BaseAgent
from app.agents.internship_agent.handlers import discover_internships

logger = logging.getLogger("agentforge.agents.internship")


class InternshipAgent(BaseAgent):
    """Handles internship opportunity discovery and recommendations."""

    agent_type = "internship"

    async def execute(self, params: dict) -> dict:
        return await discover_internships(self.user_id, params, self.db)
