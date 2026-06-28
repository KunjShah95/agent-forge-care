import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agentforge.auth")

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserOut,
    UserUpdate,
)

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user."""
    try:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        await db.flush()
        return user
    except Exception as e:
        logger.error("Failed to update user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
