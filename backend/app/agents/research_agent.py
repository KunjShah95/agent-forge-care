"""
Research Agent — backward-compat re-export layer.

All logic moved to research_agent/handlers.py.
This module exists so existing imports continue to work.
New code should import from the handler module directly.
"""

from app.agents.research_agent.handlers import (  # noqa: F401
    conduct_research,
    retrieve_research_context,
)
