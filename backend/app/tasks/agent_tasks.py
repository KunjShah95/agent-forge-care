import asyncio
import logging
from typing import Any

from app.models.user import AgentTask, TaskStatus
from app.db.session import async_session
from app.agents.research_agent import conduct_research


logger = logging.getLogger("agentforge.tasks")


def process_research_task(task_id: str, user_id: str, query: str, focus: str) -> None:
    """RQ worker entrypoint — runs inside worker process (sync function).

    It runs the async conduct_research coroutine using asyncio.
    Updates AgentTask status in the DB.
    """
    try:
        asyncio.run(_run_task(task_id, user_id, query, focus))
    except Exception:
        logger.exception("process_research_task failed")


async def _run_task(task_id: str, user_id: str, query: str, focus: str) -> None:
    async with async_session() as db:
        # mark running
        t = await db.get(AgentTask, task_id)
        if not t:
            logger.error("AgentTask not found: %s", task_id)
            return
        t.status = TaskStatus.running
        await db.commit()

        try:
            res = await conduct_research(user_id, {"query": query, "focus": focus}, db)
            t.output = res
            t.status = TaskStatus.completed
            await db.commit()
        except Exception as e:
            logger.exception("Research agent failed for task %s", task_id)
            t.status = TaskStatus.failed
            t.error = str(e)
            await db.commit()