"""Monitor Agent handlers — opportunity scanning and alerts."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agentforge.agents.monitor.handlers")


async def run_daily_scan(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Run the daily opportunity monitor scan."""
    from app.opportunity_agent.service import OpportunityAgentService

    search_query = params.get("search_query")

    try:
        service = OpportunityAgentService(db, user_id)
        result = await service.run_scan(search_query=search_query)
        return {
            "items": [i.model_dump() for i in result.items],
            "total": result.total, "scored": result.scored,
            "alerts": result.alerts, "message": result.message,
            "analysis": result.analysis.model_dump() if result.analysis else None,
            "feedback": result.feedback.model_dump() if result.feedback else None,
        }
    except Exception as e:
        logger.error("Daily scan failed for user %s: %s", user_id, str(e))
        return {"items": [], "total": 0, "scored": 0, "alerts": [], "message": f"Scan failed: {str(e)}"}
