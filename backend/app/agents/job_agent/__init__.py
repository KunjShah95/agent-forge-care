# Backward-compat re-exports for consumers that import handler functions
from app.agents.job_agent.handlers import (  # noqa: F401
    discover_jobs,
    get_job_recommendations,
)
from app.agents.job_agent.service import JobAgent

__all__ = [
    "JobAgent",
    "discover_jobs",
    "get_job_recommendations",
]
