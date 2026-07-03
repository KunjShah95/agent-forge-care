"""Interview Agent — interview preparation and answer review."""

import logging

from app.agents.base import BaseAgent
from app.agents.interview_agent.handlers import prepare_interview, review_interview_answer

logger = logging.getLogger("agentforge.agents.interview")


class InterviewAgent(BaseAgent):
    """Handles interview preparation and answer review."""

    agent_type = "interview"

    async def execute(self, params: dict) -> dict:
        action = params.get("action", "prepare")
        if action == "review":
            return await review_interview_answer(self.user_id, params, self.db)
        return await prepare_interview(self.user_id, params, self.db)
