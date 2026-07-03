"""Job Agent — full-time job discovery and recommendations."""

import logging

from app.agents.base import BaseAgent
from app.agents.job_agent.handlers import discover_jobs

logger = logging.getLogger("agentforge.agents.job")


class JobAgent(BaseAgent):
    """Handles full-time job opportunity discovery and recommendations."""

    agent_type = "job"

    async def execute(self, params: dict) -> dict:
        return await discover_jobs(self.user_id, params, self.db)
