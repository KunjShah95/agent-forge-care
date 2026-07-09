import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_unverified
from app.models.user import Profile, User
from app.schemas.user import UserOut, UserUpdate

logger = logging.getLogger("agentforge.auth")
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Helpers ────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user: User) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "email_verified": True,
        "type": "local",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ─── Endpoints ──────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=data.email,
        full_name=data.full_name or data.email.split("@")[0],
        password_hash=_hash_password(data.password),
        email_verified=True,
        firebase_uid=None,
    )
    db.add(user)
    await db.flush()

    db.add(Profile(user_id=user.id, is_onboarded=False))
    await db.flush()

    token = _create_token(user)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_token(user)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ─── Existing endpoints ──────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user_unverified)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user_unverified),
    db: AsyncSession = Depends(get_db),
):
    try:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        await db.flush()
        return user
    except Exception as e:
        logger.error("Failed to update user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
