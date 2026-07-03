"""Monitor Agent — opportunity scanning and alerts."""

import logging

from app.agents.base import BaseAgent
from app.agents.monitor_agent.handlers import run_daily_scan

logger = logging.getLogger("agentforge.agents.monitor")


class MonitorAgent(BaseAgent):
    """Handles opportunity monitoring scans and alerts."""

    agent_type = "monitor"

    async def execute(self, params: dict) -> dict:
        return await run_daily_scan(self.user_id, params, self.db)
