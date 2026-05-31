from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    UserOut,
    UserUpdate,
)

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_400_BAD_REQUEST,
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registration is handled via Firebase. This endpoint exists for backward compatibility."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Registration is handled via Firebase. Use POST /auth/me to sync your profile.",
    )


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login is handled via Firebase. This endpoint exists for backward compatibility."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Login is handled via Firebase. Authenticate with Firebase and use the returned ID token as a Bearer token.",
    )


@router.post("/refresh")
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Token refresh is handled via Firebase. This endpoint exists for backward compatibility."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Token refresh is handled via Firebase SDK on the client side.",
    )


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
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.flush()
    return user
