from app.agents.internship_agent.service import InternshipAgent

# Backward-compat re-exports for consumers that import handler functions
from app.agents.internship_agent.handlers import (                      # noqa: F401
    discover_internships,
    get_internship_recommendations,
)
