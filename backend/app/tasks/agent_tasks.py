import asyncio
import logging

from app.models.user import AgentTask, TaskStatus
from app.database import async_session_factory as async_session
from app.agents.research_agent import conduct_research
from app.services.profile_scraper import scrape_github_profile, analyze_github_for_skills, scrape_portfolio
from app.services.memory_service import MemoryService


logger = logging.getLogger("agentforge.tasks")


def _run_async(coro):
    """Run an async coroutine from a sync RQ worker context.
    Uses the existing event loop if one exists, otherwise creates a new one.
    This avoids blocking the worker thread pool with nested asyncio.run() calls.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop is already running (e.g., in tests or async context)
            import threading
            result = []
            exception = []
            def _run():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result.append(new_loop.run_until_complete(coro))
                except Exception as e:
                    exception.append(e)
                finally:
                    new_loop.close()
            thread = threading.Thread(target=_run)
            thread.start()
            thread.join()
            if exception:
                raise exception[0]
            return result[0] if result else None
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def process_research_task(task_id: str, user_id: str, query: str, focus: str) -> None:
    """RQ worker entrypoint — runs inside worker process (sync function)."""
    try:
        _run_async(_run_task(task_id, user_id, query, focus))
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


def process_github_scrape(task_id: str, user_id: str, github_url: str) -> None:
    """RQ worker entrypoint: scrape a GitHub user profile and store results."""
    try:
        _run_async(_run_github_scrape(task_id, user_id, github_url))
    except Exception:
        logger.exception("process_github_scrape failed")


async def _run_github_scrape(task_id: str, user_id: str, github_url: str) -> None:
    """Scrape GitHub profile, analyze for skills, and store in memory."""
    raw_data = await scrape_github_profile(github_url)
    analysis = await analyze_github_for_skills(raw_data)

    async with async_session() as db:
        mem = MemoryService(db)

        # Store raw scraped data
        await mem.set_memory(user_id, "github_profile_raw", raw_data, weight=0.8)

        # Store skill/analysis results
        await mem.set_memory(user_id, "github_skills_analysis", analysis, weight=0.9)

        # Mark task complete
        if task_id:
            t = await db.get(AgentTask, task_id)
            if t:
                t.status = TaskStatus.completed
                t.output = {"raw_data_summary": {k: v for k, v in raw_data.items() if k != "repositories"}, "analysis": analysis}
                await db.commit()


def process_portfolio_scrape(task_id: str, user_id: str, portfolio_url: str) -> None:
    """RQ worker entrypoint: scrape a portfolio website and store results."""
    try:
        _run_async(_run_portfolio_scrape(task_id, user_id, portfolio_url))
    except Exception:
        logger.exception("process_portfolio_scrape failed")


async def _run_portfolio_scrape(task_id: str, user_id: str, portfolio_url: str) -> None:
    """Scrape portfolio page and store structured results in memory."""
    scraped = await scrape_portfolio(portfolio_url)

    async with async_session() as db:
        mem = MemoryService(db)
        await mem.set_memory(user_id, "portfolio_scrape", scraped, weight=0.8)

        if task_id:
            t = await db.get(AgentTask, task_id)
            if t:
                t.status = TaskStatus.completed
                t.output = scraped
                await db.commit()