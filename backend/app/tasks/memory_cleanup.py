"""
Periodic task: delete expired memory entries.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import async_session_factory
from app.models.user import MemoryEntry

logger = logging.getLogger("agentforge.tasks.memory_cleanup")


async def cleanup_expired_memory():
    """Delete all memory entries where ttl_days is set and entry is past its TTL."""
    async with async_session_factory() as db:
        now = datetime.now(UTC)
        result = await db.execute(select(MemoryEntry).where(MemoryEntry.ttl_days.isnot(None)))
        entries = result.scalars().all()
        deleted = 0
        for entry in entries:
            expires_at = entry.created_at + timedelta(days=entry.ttl_days)
            if now > expires_at:
                await db.delete(entry)
                deleted += 1
        await db.commit()
        if deleted:
            logger.info("Memory cleanup: deleted %d expired entries", deleted)
