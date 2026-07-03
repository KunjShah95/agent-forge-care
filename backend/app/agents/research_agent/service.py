"""Research Agent — company research, interview insights, and market intelligence."""

import logging

from app.agents.base import BaseAgent
from app.agents.research_agent.handlers import conduct_research

logger = logging.getLogger("agentforge.agents.research")


class ResearchAgent(BaseAgent):
    """Handles company research, interview preparation, and market intelligence."""

    agent_type = "research"

    async def execute(self, params: dict) -> dict:
        return await conduct_research(self.user_id, params, self.db)
