"""Resume Agent — resume tailoring and cover letter generation."""

import logging

from app.agents.base import BaseAgent
from app.agents.resume_agent.handlers import tailor_resume, generate_cover_letter

logger = logging.getLogger("agentforge.agents.resume")


class ResumeAgent(BaseAgent):
    """Handles resume tailoring and cover letter generation."""

    agent_type = "resume"

    async def execute(self, params: dict) -> dict:
        action = params.get("action", "tailor")
        if action == "cover_letter":
            return await generate_cover_letter(self.user_id, params, self.db)
        return await tailor_resume(self.user_id, params, self.db)
