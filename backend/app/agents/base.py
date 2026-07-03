import logging
import time
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import AgentResult, AgentStatus

logger = logging.getLogger("agentforge.agents.base")


def strip_json_fences(content) -> str:
    """Strip markdown code fences and 'json' prefix from LLM responses."""
    content = str(content).strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    if content.startswith("json"):
        content = content[4:].strip()
    return content


class BaseAgent:
    agent_type: str = "base"
    AGENT_REGISTRY: dict[str, type["BaseAgent"]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.agent_type and cls.agent_type != "base":
            cls.AGENT_REGISTRY[cls.agent_type] = cls
            logger.debug("Registered agent type=%s class=%s", cls.agent_type, cls.__name__)

    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def run(self, params: dict) -> AgentResult:
        start = time.monotonic()
        task_id = str(uuid.uuid4())
        try:
            output = await self.execute(params)
            elapsed = time.monotonic() - start
            return AgentResult(
                task_id=task_id,
                agent_type=self.agent_type,
                status=AgentStatus.COMPLETED,
                output=output,
                duration_ms=round(elapsed * 1000, 1),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.exception("Agent %s failed after %.1fs: %s", self.agent_type, elapsed, e)
            return AgentResult(
                task_id=task_id,
                agent_type=self.agent_type,
                status=AgentStatus.FAILED,
                error=str(e),
                duration_ms=round(elapsed * 1000, 1),
            )

    async def execute(self, params: dict) -> dict:
        raise NotImplementedError
