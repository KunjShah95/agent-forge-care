"""
LangGraph persistent checkpointer backed by PostgreSQL.

Provides an ``AsyncPostgresSaver`` that survives restarts and enables
state recovery for planner pipeline runs.

Falls back to in-memory ``MemorySaver`` when
``langgraph-checkpoint-postgres`` is not installed.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

logger = logging.getLogger("agentforge.checkpointer")

# ── Module-level state (initialized lazily) ──────────────────

_engine: AsyncEngine | None = None
_checkpointer: Any = None  # AsyncPostgresSaver or MemorySaver
_init_lock = asyncio.Lock()


def _build_engine() -> AsyncEngine:
    """Build an async engine dedicated to checkpoint storage.

    Uses the same DATABASE_URL as the main app but with a smaller pool
    since checkpoint traffic is much lower than query traffic.
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
        connect_args={"timeout": 10},
    )


async def get_checkpointer() -> Any:
    """Return the global checkpointer instance.

    Lazy-initialized on first call with a lock to prevent races.
    The engine is created once and reused for the lifetime of the process.
    """
    global _engine, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    async with _init_lock:
        # Double-check after acquiring the lock
        if _checkpointer is not None:
            return _checkpointer

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError:
            logger.warning(
                "langgraph-checkpoint-postgres not installed — "
                "falling back to in-memory checkpointer"
            )
            from langgraph.checkpoint.memory import MemorySaver

            _checkpointer = MemorySaver()
            return _checkpointer

        _engine = _build_engine()
        _checkpointer = AsyncPostgresSaver(_engine)

        # Create checkpoint tables (idempotent — uses CREATE TABLE IF NOT EXISTS)
        await _checkpointer.setup()
        logger.info("LangGraph PostgresSaver checkpointer initialized")

        return _checkpointer


async def close_checkpointer() -> None:
    """Dispose of the checkpointer engine on shutdown."""
    global _engine, _checkpointer

    if _engine is not None:
        await _engine.dispose()
        logger.info("LangGraph checkpointer engine disposed")

    _engine = None
    _checkpointer = None
