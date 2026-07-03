"""
Job Agent — backward-compat re-export layer.

All logic moved to job_agent/handlers.py.
This module exists so existing imports of ``from app.agents.job_agent import discover_jobs``
continue to work. New code should import from the handler module directly.
"""

from app.agents.job_agent.handlers import discover_jobs, get_job_recommendations  # noqa: F401
