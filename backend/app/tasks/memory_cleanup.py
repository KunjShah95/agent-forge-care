"""
Periodic data retention task.

Cleans up stale records across all tables based on configurable TTLs:
  - Opportunities marked inactive or past retention period
  - Applications in terminal stages (rejected/withdrawn) past retention
  - Agent tasks that are completed/failed past retention
  - Notifications (MemoryEntry with key "notification:*") past retention
  - General memory entries past their per-entry ttl_days
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.config import settings
from app.database import async_session_factory
from app.models.user import (
    AgentTask,
    Application,
    ApplicationStage,
    MemoryEntry,
    Opportunity,
    TaskStatus,
)

logger = logging.getLogger("agentforge.tasks.data_retention")


async def cleanup_expired_memory() -> int:
    """Delete memory entries past their per-entry ttl_days. Returns count deleted."""
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
        if deleted:
            logger.info("Memory cleanup: deleted %d expired memory entries", deleted)
        await db.commit()
        return deleted


async def cleanup_stale_opportunities() -> int:
    """Delete old inactive opportunities past the retention period."""
    async with async_session_factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_opportunity_days)
        result = await db.execute(
            select(Opportunity).where(
                Opportunity.is_active == False,  # noqa: E712
                Opportunity.created_at < cutoff,
            )
        )
        opportunities = result.scalars().all()
        count = len(opportunities)
        for opp in opportunities:
            await db.delete(opp)
        if count:
            logger.info("Data retention: deleted %d stale opportunities (older than %d days)", count, settings.data_retention_opportunity_days)
        await db.commit()
        return count


async def cleanup_stale_applications() -> int:
    """Delete applications in terminal stages past the retention period."""
    async with async_session_factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_application_days)
        terminal_stages = (ApplicationStage.rejected, ApplicationStage.withdrawn)
        result = await db.execute(
            select(Application).where(
                Application.stage.in_(terminal_stages),
                Application.created_at < cutoff,
            )
        )
        apps = result.scalars().all()
        count = len(apps)
        for app in apps:
            await db.delete(app)
        if count:
            logger.info("Data retention: deleted %d stale applications (older than %d days)", count, settings.data_retention_application_days)
        await db.commit()
        return count


async def cleanup_stale_agent_tasks() -> int:
    """Delete completed/failed agent tasks past the retention period."""
    async with async_session_factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_agent_task_days)
        terminal_statuses = (TaskStatus.completed, TaskStatus.failed)
        result = await db.execute(
            select(AgentTask).where(
                AgentTask.status.in_(terminal_statuses),
                AgentTask.created_at < cutoff,
            )
        )
        tasks = result.scalars().all()
        count = len(tasks)
        for task in tasks:
            await db.delete(task)
        if count:
            logger.info("Data retention: deleted %d stale agent tasks (older than %d days)", count, settings.data_retention_agent_task_days)
        await db.commit()
        return count


async def cleanup_stale_notifications() -> int:
    """Delete notification MemoryEntry records past the retention period."""
    async with async_session_factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_notification_days)
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.key.startswith("notification:"),
                MemoryEntry.created_at < cutoff,
            )
        )
        entries = result.scalars().all()
        count = len(entries)
        for entry in entries:
            await db.delete(entry)
        if count:
            logger.info("Data retention: deleted %d stale notifications (older than %d days)", count, settings.data_retention_notification_days)
        await db.commit()
        return count


async def run_full_data_retention() -> dict[str, int]:
    """
    Run all data retention cleanup tasks and return counts per category.
    Called by the background task in main.py.
    """
    counts = {}
    counts["memory"] = await cleanup_expired_memory()
    counts["opportunities"] = await cleanup_stale_opportunities()
    counts["applications"] = await cleanup_stale_applications()
    counts["agent_tasks"] = await cleanup_stale_agent_tasks()
    counts["notifications"] = await cleanup_stale_notifications()
    total = sum(counts.values())
    if total:
        logger.info("Data retention complete: deleted %d total records (%s)", total, counts)
    return counts
