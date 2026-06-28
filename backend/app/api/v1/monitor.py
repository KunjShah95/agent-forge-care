import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, AlertConfig

logger = logging.getLogger("agentforge.monitor")
from app.schemas.user import (
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertConfigOut,
    AlertConfigList,
    MonitorSettingsUpdate,
)

router = APIRouter()


@router.get("/alerts", response_model=AlertConfigList)
async def list_alert_configs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all alert configurations."""
    try:
        count_result = await db.execute(
            select(func.count())
            .select_from(AlertConfig)
            .where(AlertConfig.user_id == user.id)
        )
        total = count_result.scalar()

        offset = (page - 1) * limit
        result = await db.execute(
            select(AlertConfig)
            .where(AlertConfig.user_id == user.id)
            .order_by(desc(AlertConfig.created_at))
            .offset(offset)
            .limit(limit)
        )
        return AlertConfigList(
            items=[AlertConfigOut.model_validate(c) for c in result.scalars().all()],
            total=total,
            page=page,
        )
    except Exception as e:
        logger.error("Failed to list alert configs for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list alert configs: {str(e)}")


@router.post("/alerts", response_model=AlertConfigOut, status_code=201)
async def create_alert_config(
    data: AlertConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert configuration."""
    try:
        config = AlertConfig(user_id=user.id, **data.model_dump())
        db.add(config)
        await db.flush()
        return config
    except Exception as e:
        logger.error("Failed to create alert config for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create alert config: {str(e)}")


@router.patch("/alerts/{id}", response_model=AlertConfigOut)
async def update_alert_config(
    id: str,
    data: AlertConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an alert configuration."""
    try:
        result = await db.execute(
            select(AlertConfig).where(AlertConfig.id == id, AlertConfig.user_id == user.id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Alert config not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)
        await db.flush()
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update alert config for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update alert config: {str(e)}")


@router.delete("/alerts/{id}", status_code=204)
async def delete_alert_config(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert configuration."""
    try:
        result = await db.execute(
            select(AlertConfig).where(AlertConfig.id == id, AlertConfig.user_id == user.id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Alert config not found")
        await db.delete(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete alert config for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete alert config: {str(e)}")


@router.get("/settings")
async def get_monitor_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get opportunity monitor settings."""
    try:
        from app.models.user import MemoryEntry

        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key == "monitor_settings",
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            return entry.value
        return {
            "frequency": "daily",
            "digest": True,
            "push": False,
            "realtime": False,
            "min_match_score": 80,
        }
    except Exception as e:
        logger.error("Failed to get monitor settings for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get monitor settings: {str(e)}")


@router.patch("/settings")
async def update_monitor_settings(
    data: MonitorSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update opportunity monitor settings."""
    try:
        from app.models.user import MemoryEntry

        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key == "monitor_settings",
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.value = data.model_dump(exclude_unset=True)
        else:
            entry = MemoryEntry(
                user_id=user.id,
                key="monitor_settings",
                value=data.model_dump(exclude_unset=True),
            )
            db.add(entry)
        await db.flush()
        return {"status": "updated"}
    except Exception as e:
        logger.error("Failed to update monitor settings for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update monitor settings: {str(e)}")
