from app.agents.research_agent.service import ResearchAgent

# Backward-compat re-exports for tests that import private helper functions
from app.agents.research_agent.handlers import (                      # noqa: F401
    conduct_research,
    retrieve_research_context,
    _fallback_company_info as _research_company,
    _fallback_interview_insights as _interview_insights,
    _fallback_market_intelligence as _market_intelligence,
    _fallback_skill_insights as _skill_insights,
)
