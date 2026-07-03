"""
Internship Agent — backward-compat re-export layer.

All logic moved to internship_agent/handlers.py.
This module exists so existing imports of ``from app.agents.internship_agent import discover_internships``
continue to work. New code should import from the handler module directly.
"""

from app.agents.internship_agent.handlers import discover_internships, get_internship_recommendations  # noqa: F401
