"""
Scheduled background task: scans for hackathons periodically for users
who have hackathon alerts enabled.

Runs as an asyncio background loop, launched during the FastAPI lifespan.
Checks the in-memory preference store every 6 hours and triggers the
hackathon scan for each opted-in user by calling the shared scan logic.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.database import async_session_factory
from app.models.user import MemoryEntry
from sqlalchemy import select

from app.api.v1.opportunities import _run_hackathon_scan

logger = logging.getLogger("agentforge.tasks.hackathon_scanner")

# ─── Configuration ──────────────────────────────────────────

HACKATHON_SCAN_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
"""How often to run the periodic hackathon scan."""

HACKATHON_ALERT_MEMORY_KEY = "hackathon_alert_enabled"
"""Memory entry key that stores whether a user has opted into hackathon alerts."""


# ─── Scanner Logic ──────────────────────────────────────────


async def _get_alert_users() -> list[str]:
    """Query memory entries to find all users who have hackathon alerts enabled."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.key == HACKATHON_ALERT_MEMORY_KEY,
            )
        )
        entries = result.scalars().all()

        enabled_users: list[str] = []
        for entry in entries:
            if entry.value is True:
                enabled_users.append(entry.user_id)

        return enabled_users


async def _should_scan_user(user_id: str) -> bool:
    """Check if enough time has passed since the last scan.

    Returns True if the last scan was more than 6 hours ago or never ran.
    """
    async with async_session_factory() as db:
        from app.services.memory_service import MemoryService

        memory = MemoryService(db)
        last_scan = await memory.get_memory(str(user_id), "last_hackathon_scan")

        if not last_scan:
            return True  # Never scanned before

        timestamp_str = None
        if isinstance(last_scan, dict):
            timestamp_str = last_scan.get("timestamp")

        if not timestamp_str:
            return True

        try:
            last_time = datetime.fromisoformat(timestamp_str)
            elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
            return elapsed >= HACKATHON_SCAN_INTERVAL
        except (ValueError, TypeError):
            return True


async def run_scheduled_hackathon_scan() -> None:
    """
    Background loop: every 6 hours, scan for hackathons for all opted-in users.

    Runs as an asyncio task during the FastAPI lifespan.
    Calls the shared _run_hackathon_scan function to avoid code duplication.
    """
    logger.info("Hackathon scanner started (interval: %d seconds)", HACKATHON_SCAN_INTERVAL)

    while True:
        try:
            alert_users = await _get_alert_users()
            logger.info(
                "Scheduled hackathon scan: %d users with alerts enabled",
                len(alert_users),
            )

            scanned = 0
            for user_id in alert_users:
                if await _should_scan_user(user_id):
                    logger.debug("Scanning hackathons for user %s", user_id)
                    async with async_session_factory() as db:
                        try:
                            # Check if user has email notifications enabled
                            from app.services.memory_service import MemoryService
                            mem = MemoryService(db)
                            email_pref = await mem.get_memory(
                                str(user_id), "hackathon_email_enabled"
                            )
                            email_enabled = (
                                isinstance(email_pref, bool) and email_pref is True
                            )

                            # Look up user's email if email notifications are on
                            user_email: str | None = None
                            if email_enabled:
                                from app.models.user import User
                                u_result = await db.execute(
                                    select(User).where(User.id == user_id)
                                )
                                user_obj = u_result.scalar_one_or_none()
                                if user_obj:
                                    user_email = user_obj.email

                            result = await _run_hackathon_scan(
                                db=db,
                                user_id=str(user_id),
                                skills=None,
                                persist_alert=None,
                                persist_email=None,
                                user_email=user_email,
                            )
                            scanned += 1
                            logger.info(
                                "Hackathon scan for user %s: %s",
                                user_id,
                                result.get("message", "completed"),
                            )
                        except Exception as e:
                            logger.error(
                                "Hackathon scan failed for user %s: %s",
                                user_id,
                                str(e),
                            )

                    # Small delay between users to avoid rate-limiting search APIs
                    await asyncio.sleep(0.5)

            if scanned > 0 or alert_users:
                logger.info(
                    "Scheduled hackathon scan complete: %d/%d users scanned",
                    scanned,
                    len(alert_users),
                )

        except Exception as e:
            logger.exception("Scheduled hackathon scan cycle failed: %s", e)

        await asyncio.sleep(HACKATHON_SCAN_INTERVAL)
