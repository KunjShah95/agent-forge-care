import time
import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import redis.asyncio as aioredis

from app.config import settings
from app.database import get_db
from app.models.user import User, Profile

security = HTTPBearer()

# ─── Firebase Token Verification ────────────────────────────

CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
CACHE_DURATION = 14400

_certs_cache: dict = {"certs": None, "expires_at": 0.0}


def _get_certs() -> dict:
    if time.time() < _certs_cache["expires_at"] and _certs_cache["certs"]:
        return _certs_cache["certs"]
    response = requests.get(CERTS_URL)
    response.raise_for_status()
    certs = response.json()
    _certs_cache["certs"] = certs
    _certs_cache["expires_at"] = time.time() + CACHE_DURATION
    cache_control = response.headers.get("cache-control", "")
    if "max-age=" in cache_control:
        try:
            max_age = int(cache_control.split("max-age=")[1].split(",")[0])
            _certs_cache["expires_at"] = time.time() + max_age
        except (ValueError, IndexError):
            pass
    return certs


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload."""
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise ValueError("No kid in token header")

    certs = _get_certs()
    cert_pem = certs.get(kid)
    if not cert_pem:
        raise ValueError(f"No matching cert for kid: {kid}")

    cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
    public_key = cert.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    try:
        payload = jwt.decode(
            token,
            public_pem,
            algorithms=["RS256"],
            audience=settings.firebase_project_id,
            issuer=f"https://securetoken.google.com/{settings.firebase_project_id}",
        )
        return payload
    except Exception as e:
        raise ValueError(f"Token verification failed: {e}")


# ─── Rate Limiting Key ──────────────────────────────────────


def _get_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = verify_firebase_token(auth.split(" ", 1)[1])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


# ─── Redis Rate Limiter ─────────────────────────────────────


class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def is_rate_limited(
        self, key: str, max_requests: int, window_seconds: int
    ) -> bool:
        r = await self._get_redis()
        now = time.time()
        window_start = now - window_seconds

        pipeline = r.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, window_seconds)

        _, count, _, _ = await pipeline.execute()
        return count >= max_requests


_rate_limiter_instance: RedisRateLimiter | None = None


async def rate_limiter() -> RedisRateLimiter:
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RedisRateLimiter(settings.redis_url)
    return _rate_limiter_instance


# ─── Current User ───────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Firebase token and return the current user with auto-provisioning."""
    token = credentials.credentials
    try:
        payload = verify_firebase_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    from sqlalchemy import select

    firebase_uid = payload.get("sub", "")
    email = payload.get("email", "")
    name = payload.get("name", email.split("@")[0] if email else "User")

    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            firebase_uid=firebase_uid,
            password_hash=None,
            full_name=name,
        )
        db.add(user)
        await db.flush()

        profile = Profile(user_id=user.id, is_onboarded=False)
        db.add(profile)
        await db.flush()
    elif user.firebase_uid is None and firebase_uid:
        user.firebase_uid = firebase_uid
        await db.flush()

    # Note: db.commit() is handled by get_db() context manager on request exit
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optionally authenticate — returns None if no token."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
