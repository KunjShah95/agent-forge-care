"""
GDPR compliance endpoints — data export and account deletion.

These endpoints allow users to exercise their right to data portability
(Article 20) and right to erasure (Article 17) under GDPR.
"""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import (
    AgentTask,
    Application,
    Contact,
    MemoryEntry,
    Notification,
    Opportunity,
    Profile,
    User,
)
from app.schemas.user import UserOut

logger = logging.getLogger("agentforge.gdpr")
router = APIRouter()


class DataExportResponse(BaseModel):
    """Response for GDPR data export request."""

    export: dict
    exported_at: str
    format: str = "json"


@router.get("/export", response_model=DataExportResponse)
async def export_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all user data in a machine-readable JSON format.

    Returns a complete copy of all personal data associated with the account,
    including profile, applications, contacts, agent tasks, notifications,
    and memory entries.
    """
    export = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "email_verified": user.email_verified,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": None,
        "opportunities": [],
        "applications": [],
        "contacts": [],
        "agent_tasks": [],
        "notifications": [],
        "memory_entries": [],
    }

    # Profile
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    if profile:
        export["profile"] = {
            "school": profile.school,
            "graduation_date": profile.graduation_date.isoformat() if profile.graduation_date else None,
            "bio": profile.bio,
            "portfolio_url": profile.portfolio_url,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "target_locations": profile.target_locations or [],
            "salary_min": profile.salary_min,
            "salary_max": profile.salary_max,
            "role_types": profile.role_types or [],
            "company_sizes": profile.company_sizes or [],
            "career_goal": profile.career_goal,
        }

    # Opportunities (saved matches)
    opp_result = await db.execute(
        select(Opportunity).where(
            Opportunity.id.in_(
                select(Application.opportunity_id).where(Application.user_id == user.id)
            )
        )
    )
    for opp in opp_result.scalars().all():
        export["opportunities"].append({
            "id": str(opp.id),
            "title": opp.title,
            "company": opp.company,
            "location": opp.location,
            "type": opp.type,
            "posted_date": opp.posted_date.isoformat() if opp.posted_date else None,
        })

    # Applications
    app_result = await db.execute(select(Application).where(Application.user_id == user.id))
    for app in app_result.scalars().all():
        export["applications"].append({
            "id": str(app.id),
            "opportunity_id": str(app.opportunity_id),
            "stage": app.stage,
            "applied_date": app.applied_date.isoformat() if app.applied_date else None,
            "notes": app.notes,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        })

    # Contacts
    contact_result = await db.execute(select(Contact).where(Contact.user_id == user.id))
    for c in contact_result.scalars().all():
        export["contacts"].append({
            "id": str(c.id),
            "name": c.name,
            "role": c.role,
            "company": c.company,
            "email": c.email,
            "linkedin_url": c.linkedin_url,
            "status": c.status,
            "notes": c.notes,
        })

    # Agent tasks
    task_result = await db.execute(select(AgentTask).where(AgentTask.user_id == user.id))
    for t in task_result.scalars().all():
        export["agent_tasks"].append({
            "id": str(t.id),
            "agent_type": t.agent_type.value if hasattr(t.agent_type, "value") else str(t.agent_type),
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    # Notifications
    notif_result = await db.execute(select(Notification).where(Notification.user_id == user.id))
    for n in notif_result.scalars().all():
        export["notifications"].append({
            "id": str(n.id),
            "title": n.title,
            "type": n.type,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    # Memory entries
    mem_result = await db.execute(select(MemoryEntry).where(MemoryEntry.user_id == user.id))
    for m in mem_result.scalars().all():
        export["memory_entries"].append({
            "id": str(m.id),
            "key": m.key,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        })

    logger.info("GDPR data export completed for user %s", user.id)

    return DataExportResponse(
        export=export,
        exported_at=datetime.now(UTC).isoformat(),
    )


class AccountDeletionResponse(BaseModel):
    """Response for account deletion request."""

    status: str
    message: str
    deleted_at: str


@router.delete("/account", response_model=AccountDeletionResponse)
async def delete_user_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete the user account and all associated data.

    This action is irreversible. All personal data will be removed from
    the database in compliance with GDPR Article 17 (Right to Erasure).
    """
    now = datetime.now(UTC)

    # Delete in reverse dependency order to avoid FK violations
    # 1. Notifications
    await db.execute(delete(Notification).where(Notification.user_id == user.id))
    # 2. Memory entries (including vector embeddings)
    await db.execute(delete(MemoryEntry).where(MemoryEntry.user_id == user.id))
    # 3. Agent tasks
    await db.execute(delete(AgentTask).where(AgentTask.user_id == user.id))
    # 4. Contacts
    await db.execute(delete(Contact).where(Contact.user_id == user.id))
    # 5. Applications
    await db.execute(delete(Application).where(Application.user_id == user.id))
    # 6. Profile
    await db.execute(delete(Profile).where(Profile.user_id == user.id))
    # 7. User record
    await db.delete(user)

    await db.commit()

    logger.info("GDPR account deletion completed for user %s", user.id)

    return AccountDeletionResponse(
        status="deleted",
        message="Your account and all associated data have been permanently deleted.",
        deleted_at=now.isoformat(),
    )
