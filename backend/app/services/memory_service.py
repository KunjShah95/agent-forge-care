import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import MemoryEntry

logger = logging.getLogger("agentforge.services.memory")


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_context(self, user_id: str) -> dict:
        """Get all memory entries for a user as a plain dict."""
        try:
            result = await self.db.execute(select(MemoryEntry).where(MemoryEntry.user_id == user_id))
            entries = result.scalars().all()
            context = {}
            for entry in entries:
                context[entry.key] = {
                    "value": entry.value,
                    "weight": float(entry.weight),
                }
            return context
        except Exception as e:
            logger.error("Failed to get memory context for user %s: %s", user_id, str(e))
            raise

    async def set_memory(self, user_id: str, key: str, value: Any, weight: float = 1.0, ttl_days: int | None = None):
        """Set or update a memory entry."""
        try:
            if not key or not isinstance(key, str) or len(key.strip()) < 1:
                raise ValueError("Memory key must be a non-empty string")

            result = await self.db.execute(
                select(MemoryEntry).where(
                    MemoryEntry.user_id == user_id,
                    MemoryEntry.key == key,
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.value = value
                entry.weight = weight
                if ttl_days is not None:
                    entry.ttl_days = ttl_days
            else:
                entry = MemoryEntry(
                    user_id=user_id,
                    key=key,
                    value=value,
                    weight=weight,
                    ttl_days=ttl_days if ttl_days is not None else None,
                )
                self.db.add(entry)
            await self.db.flush()
            return entry
        except Exception as e:
            logger.error("Failed to set memory '%s' for user %s: %s", key, user_id, str(e))
            raise

    async def get_memory(self, user_id: str, key: str) -> Any:
        """Get a single memory entry by key."""
        try:
            result = await self.db.execute(
                select(MemoryEntry).where(
                    MemoryEntry.user_id == user_id,
                    MemoryEntry.key == key,
                )
            )
            entry = result.scalar_one_or_none()
            return entry.value if entry else None
        except Exception as e:
            logger.error("Failed to get memory '%s' for user %s: %s", key, user_id, str(e))
            raise
