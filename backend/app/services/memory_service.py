from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import MemoryEntry


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_context(self, user_id: str) -> dict:
        """Get all memory entries for a user as a plain dict."""
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.user_id == user_id)
        )
        entries = result.scalars().all()
        context = {}
        for entry in entries:
            context[entry.key] = {
                "value": entry.value,
                "weight": float(entry.weight),
            }
        return context

    async def set_memory(self, user_id: str, key: str, value: Any, weight: float = 1.0):
        """Set or update a memory entry."""
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
        else:
            entry = MemoryEntry(
                user_id=user_id,
                key=key,
                value=value,
                weight=weight,
            )
            self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_memory(self, user_id: str, key: str) -> Any:
        """Get a single memory entry by key."""
        result = await self.db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.key == key,
            )
        )
        entry = result.scalar_one_or_none()
        return entry.value if entry else None
