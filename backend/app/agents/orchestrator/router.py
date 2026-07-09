import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator.schemas import OrchestratorRequest
from app.agents.orchestrator.service import OrchestratorAgent
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger("agentforge.api.orchestrator")
router = APIRouter()


@router.post("/run")
async def run_orchestrator(
    body: OrchestratorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = OrchestratorAgent(db, str(user.id))
    result = await agent.run({"goal": body.goal})
    return result.output or {"error": "Orchestrator returned no output"}


@router.get("/agents")
async def list_agents():
    from app.agents.orchestrator.service import AGENT_REGISTRY

    agents = sorted(AGENT_REGISTRY.keys())
    return {
        "agents": agents,
        "total": len(agents),
    }
