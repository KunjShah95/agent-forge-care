"""Discovery Agent — profile discovery from name or email."""

import logging

from app.agents.base import BaseAgent
from app.agents.discovery_agent.handlers import discover_profiles

logger = logging.getLogger("agentforge.agents.discovery")


class DiscoveryAgent(BaseAgent):
    """Discovers social profiles (GitHub, LinkedIn, Twitter, portfolio) from a name or email.

    Uses multi-source web search + LLM parsing to find profile URLs.
    Can optionally scrape found profiles for deeper enrichment.

    Actions:
        - "discover": (default) Discover all profiles for a person
        - "enrich": Discover + scrape found profiles for skills/data
    """

    agent_type = "discovery"

    async def execute(self, params: dict) -> dict:
        action = params.get("action", "discover")

        # If action is "enrich", enable scraping
        if action == "enrich":
            params["scrape"] = True

        return await discover_profiles(self.user_id, params, self.db)
