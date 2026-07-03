from app.agents.job_agent.service import JobAgent

# Backward-compat re-exports for consumers that import handler functions
from app.agents.job_agent.handlers import (                              # noqa: F401
    discover_jobs,
    get_job_recommendations,
)
