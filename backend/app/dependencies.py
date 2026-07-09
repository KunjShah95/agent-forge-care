import time

import httpx
import redis.asyncio as aioredis
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import Profile, User

security = HTTPBearer(auto_error=False)

# ─── Firebase Token Verification ────────────────────────────

CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
CACHE_DURATION = 14400  # 4 hours default
MAX_CACHE_DURATION = 86400  # 24 hours max from cache-control
HTTP_TIMEOUT = 10  # seconds

_certs_cache: dict = {"certs": None, "expires_at": 0.0}

# Shared httpx sync Client with connection pooling (used by verify_firebase_token
# which is called from both sync and async contexts, so it must stay sync)
_httpx_sync_client: httpx.Client | None = None


def _get_sync_client() -> httpx.Client:
    """Get or create a shared sync HTTP client."""
    global _httpx_sync_client
    if _httpx_sync_client is None:
        _httpx_sync_client = httpx.Client(timeout=HTTP_TIMEOUT)
    return _httpx_sync_client


def _get_certs_sync() -> dict:
    """Fetch Firebase public certificates (sync, for compatibility with both sync and async contexts)."""
    if time.time() < _certs_cache["expires_at"] and _certs_cache["certs"]:
        return _certs_cache["certs"]

    client = _get_sync_client()
    response = client.get(CERTS_URL)
    response.raise_for_status()
    certs = response.json()
    _certs_cache["certs"] = certs

    # Use cache-control max-age if present and within bounds
    expires_at = time.time() + CACHE_DURATION
    cache_control = response.headers.get("cache-control", "")
    if "max-age=" in cache_control:
        try:
            max_age = int(cache_control.split("max-age=")[1].split(",")[0])
            max_age = min(max_age, MAX_CACHE_DURATION)  # Cap at 24h
            expires_at = time.time() + max_age
        except (ValueError, IndexError):
            pass

    _certs_cache["expires_at"] = expires_at
    return certs


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload."""
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise ValueError("No kid in token header")

    try:
        certs = _get_certs_sync()
    except Exception as e:
        # Fall back to cached certs if available, then raise
        if _certs_cache["certs"]:
            certs = _certs_cache["certs"]
        else:
            raise ValueError(f"Failed to fetch Firebase certs: {e}")

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

# Auth route prefix patterns that get stricter rate limiting
AUTH_ROUTE_PREFIXES = ("/api/v1/auth/", "/auth/")


def _is_auth_route(request: Request) -> bool:
    """Check if the request targets an auth endpoint (login/register)."""
    path = request.url.path.lower()
    return any(path.startswith(p.lower()) for p in AUTH_ROUTE_PREFIXES)


def _get_rate_limit_config(request: Request) -> tuple[int, int]:
    """
    Get (max_requests, window_seconds) for the request.
    Auth routes get a stricter limit to prevent brute force.
    """
    if _is_auth_route(request):
        return (settings.auth_rate_limit_per_minute, 60)
    return (settings.rate_limit_per_minute, 60)


def _get_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = verify_firebase_token(auth.split(" ", 1)[1])
            user_id = payload.get("sub")
            if user_id:
                prefix = "auth_user" if _is_auth_route(request) else "user"
                return f"{prefix}:{user_id}"
        except Exception:
            pass
    client_host = request.client.host if request.client else "unknown"
    prefix = "auth_ip" if _is_auth_route(request) else "ip"
    return f"{prefix}:{client_host}"


# ─── Redis Rate Limiter ─────────────────────────────────────


class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True,
            )
        return self._redis

    async def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
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

    async def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in the current window."""
        try:
            r = await self._get_redis()
            now = time.time()
            window_start = now - window_seconds
            await r.zremrangebyscore(key, 0, window_start)
            count = await r.zcard(key)
            return max(0, max_requests - count)
        except Exception:
            return max_requests  # Fail open for remaining count


_rate_limiter_instance: RedisRateLimiter | None = None
_in_memory_rate_limiter: dict[str, list[float]] = {}  # Fallback when Redis is down


async def rate_limiter() -> RedisRateLimiter:
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RedisRateLimiter(settings.redis_url)
    return _rate_limiter_instance


def _in_memory_is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """In-memory fallback rate limiter when Redis is unavailable."""
    now = time.time()
    window_start = now - window_seconds
    timestamps = _in_memory_rate_limiter.get(key, [])
    # Prune expired timestamps
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= max_requests:
        return True
    timestamps.append(now)
    # Limit memory growth
    if len(timestamps) > max_requests * 2:
        timestamps = timestamps[-max_requests:]
    _in_memory_rate_limiter[key] = timestamps
    return False


# ─── Helpers ────────────────────────────────────────────────


def _verify_local_token(token: str) -> dict:
    """Verify a locally-issued HS256 JWT and return its payload."""
    from jose import JWTError, jwt as jose_jwt
    try:
        payload = jose_jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "local":
            raise ValueError("Not a local token")
        return payload
    except JWTError as e:
        raise ValueError(f"Local token invalid: {e}")


async def _resolve_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> tuple[User, dict]:
    """
    Verify token (local JWT first, then Firebase) and return (user, payload).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    token = credentials.credentials
    from sqlalchemy import select

    # ── Try local JWT first ──────────────────────────────────
    try:
        payload = _verify_local_token(token)
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user, payload
    except (ValueError, Exception):
        pass  # fall through to Firebase

    # ── Try Firebase token ───────────────────────────────────
    try:
        payload = verify_firebase_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    firebase_uid = payload.get("sub", "")
    email = payload.get("email", "")
    name = payload.get("name", email.split("@")[0] if email else "User")
    email_verified = payload.get("email_verified", False)

    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            email_verified=email_verified,
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

    return user, payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate Firebase token, return the current user with auto-provisioning.
    Requires email to be verified. Use get_current_user_unverified for
    endpoints where users need to check their verification status.
    """
    user, payload = await _resolve_user_from_token(credentials, db)

    email_verified = payload.get("email_verified", False)
    if user.email_verified != email_verified:
        user.email_verified = email_verified
        await db.flush()

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("Email not verified. Please verify your email address before using this feature."),
            headers={"X-Email-Verification-Required": "true"},
        )

    # Note: db.commit() is handled by get_db() context manager on request exit
    return user


async def get_current_user_unverified(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate Firebase token and return the current user without requiring
    email verification. Used for auth/profile endpoints where users need
    to check or resend verification before they've verified.
    """
    user, payload = await _resolve_user_from_token(credentials, db)

    email_verified = payload.get("email_verified", False)
    if user.email_verified != email_verified:
        user.email_verified = email_verified
        await db.flush()

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optionally authenticate — returns None if no token."""
    if credentials is None:
        return None
    try:
        return await get_current_user_unverified(credentials, db)
    except HTTPException:
        return None
