import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, MemoryEntry
from app.schemas.user import NotificationOut, NotificationList

logger = logging.getLogger("agentforge.notifications")

router = APIRouter()


@router.get("", response_model=NotificationList)
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch notifications for the current user."""
    result = await db.execute(
        select(MemoryEntry)
        .where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key.startswith("notification:"),
        )
        .order_by(MemoryEntry.created_at.desc())
        .limit(50)
    )
    entries = result.scalars().all()
    items = []
    for entry in entries:
        val = entry.value or {}
        items.append(
            NotificationOut(
                id=str(entry.id),
                title=val.get("title", ""),
                body=val.get("body", ""),
                type=val.get("type", "info"),
                read=val.get("read", False),
                created_at=entry.created_at,
            )
        )
    return NotificationList(items=items)


@router.patch("/{id}", response_model=NotificationOut)
async def mark_notification_read(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    # Input validation
    if not id or not isinstance(id, str) or len(id.strip()) < 1:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.id == id,
                MemoryEntry.user_id == user.id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="Notification not found")
        val = dict(entry.value or {})
        val["read"] = True
        entry.value = val
        await db.flush()
        return NotificationOut(
            id=str(entry.id),
            title=val.get("title", ""),
            body=val.get("body", ""),
            type=val.get("type", "info"),
            read=True,
            created_at=entry.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")


@router.post("/read-all")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    try:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key.startswith("notification:"),
            )
        )
        entries = result.scalars().all()
        for entry in entries:
            val = dict(entry.value or {})
            val["read"] = True
            entry.value = val
        await db.flush()
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to mark all notifications as read for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to mark all notifications as read: {str(e)}")
