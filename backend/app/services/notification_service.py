import logging
import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger("agentforge.notifications")

NotificationType = Literal["success", "error", "info"]


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    body: str = "",
    type: NotificationType = "info",
    to_email: str | None = None,
) -> None:
    """Create an in-app notification for a user via the memory system.
    Optionally delivers via email when to_email is provided.

    Notifications automatically expire after DATA_RETENTION_NOTIFICATION_DAYS.
    """
    memory = MemoryService(db)
    await memory.set_memory(
        user_id,
        f"notification:{uuid.uuid4()}",
        {
            "title": title,
            "body": body,
            "type": type,
            "read": False,
        },
        weight=1.0,
        ttl_days=settings.data_retention_notification_days,
    )
    logger.debug("Notification created for user %s: %s (TTL: %d days)", user_id, title, settings.data_retention_notification_days)

    if to_email:
        from app.services.email_service import send_email

        await send_email(to_email=to_email, subject=title, body=body)
