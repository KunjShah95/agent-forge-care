from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, limiter
from app.models.user import User
from app.schemas.user import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
async def register(
    request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)
):
    """Create a new user account."""
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=AuthService.hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()

    return TokenResponse(
        access_token=AuthService.create_access_token(str(user.id)),
        refresh_token=AuthService.create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)
):
    """Authenticate and get JWT tokens."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not AuthService.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(
        access_token=AuthService.create_access_token(str(user.id)),
        refresh_token=AuthService.create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request, data: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Refresh an access token using a valid refresh token."""
    try:
        payload = jwt.decode(
            data.token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return TokenResponse(
        access_token=AuthService.create_access_token(user_id),
        refresh_token=AuthService.create_refresh_token(user_id),
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
