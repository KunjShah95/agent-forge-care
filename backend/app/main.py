import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.api.router import router as api_router
from app.config import settings
from app.database import close_db, get_db, init_db
from app.dependencies import _get_rate_limit_config, _get_rate_limit_key, rate_limiter
from app.memory.qdrant_client import get_qdrant_client, init_collections
from app.middleware.auth import RequestLogMiddleware
from app.tasks.hackathon_scanner import run_scheduled_hackathon_scan
from app.tasks.memory_cleanup import cleanup_expired_memory

# ─── Log Sanitization ──────────────────────────────────────
# Patterns that match sensitive data in log messages
_SENSITIVE_PATTERNS = [
    (
        re.compile(r"(?i)(password|secret|token|key|authorization|bearer\s+)[=:\s]*[\w\-._~+/]{8,}"),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"(?i)(api[_-]?key)[=:\s]*[\w\-._~+/]{8,}"), r"\1=***REDACTED***"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "***EMAIL***"),
]


def sanitize_log_message(msg: str) -> str:
    """Remove sensitive information from log messages before logging."""
    sanitized = msg
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SanitizedLogger:
    """Logger wrapper that auto-sanitizes sensitive data from all log messages."""

    def __init__(self, logger):
        self._logger = logger

    def _sanitize(self, args, kwargs):
        sanitized_args = [sanitize_log_message(str(a)) if isinstance(a, str) else a for a in args]
        if "exc_info" in kwargs and kwargs["exc_info"]:
            # Don't sanitize exc_info — it's formatted separately and we never
            # log raw exception messages that contain user data
            pass
        return sanitized_args, kwargs

    def debug(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.debug(*a, **k)

    def info(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.info(*a, **k)

    def warning(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.warning(*a, **k)

    def error(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.error(*a, **k)

    def exception(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.exception(*a, **k)

    def critical(self, *args, **kwargs):
        a, k = self._sanitize(args, kwargs)
        self._logger.critical(*a, **k)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


handler = logging.StreamHandler()
handler.setFormatter(
    JSONFormatter()
    if not settings.debug
    else logging.Formatter("%(asctime)s | %(name)-12s | %(levelname)-5s | %(message)s")
)
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    handlers=[handler],
)
_raw_logger = logging.getLogger("agentforge")
# Wrap with sanitization to automatically redact sensitive data from logs
logger = SanitizedLogger(_raw_logger)


_cleanup_task = None


async def _run_memory_cleanup_loop():
    """Run cleanup_expired_memory every hour."""
    while True:
        try:
            await cleanup_expired_memory()
        except Exception:
            logger.exception("Memory cleanup cycle failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    global _cleanup_task
    logger.info("Starting %s...", settings.app_name)
    await init_db()
    logger.info("Database tables created / verified")
    try:
        init_collections()
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.warning("Qdrant init skipped: %s", e)
    _cleanup_task = asyncio.create_task(_run_memory_cleanup_loop())
    logger.info("Memory cleanup background task started")
    _hackathon_scanner_task = asyncio.create_task(run_scheduled_hackathon_scan())
    logger.info("Hackathon scanner background task started")
    yield
    if _cleanup_task:
        _cleanup_task.cancel()
    if _hackathon_scanner_task:
        _hackathon_scanner_task.cancel()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered personal career operating system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ─── Global Exception Handler (A-2: Centralized error handling) ─────


class AppError(Exception):
    """Base application error with sanitized message."""

    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        self.status_code = status_code
        self.detail = detail or message
        # Store sanitized version for logs
        self.sanitized_message = sanitize_log_message(message)
        super().__init__(self.sanitized_message)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that returns consistent JSON error responses."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    # Log the sanitized error
    logger.error(
        "Unhandled error: %s %s -> %s",
        request.method,
        request.url.path,
        sanitize_log_message(str(exc)),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# Security middleware
if not settings.debug:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["agentforge.ai", "www.agentforge.ai"])
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS middleware with stricter settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "X-CSRF-Token",
    ],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request logging middleware
app.add_middleware(RequestLogMiddleware)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    max_req, window_sec = _get_rate_limit_config(request)
    response.headers["X-RateLimit-Limit"] = str(max_req)
    try:
        from app.dependencies import _get_rate_limit_key, rate_limiter

        limiter = await rate_limiter()
        key = _get_rate_limit_key(request)
        remaining = await limiter.get_remaining(key, max_req, window_sec)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    except Exception:
        response.headers["X-RateLimit-Remaining"] = str(max_req)
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window_sec)

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.debug:
        return await call_next(request)
    max_req, window_sec = _get_rate_limit_config(request)
    try:
        limiter = await rate_limiter()
        key = _get_rate_limit_key(request)
        if await limiter.is_rate_limited(key, max_requests=max_req, window_seconds=window_sec):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Please slow down and try again later.",
                    "retry_after": window_sec,
                    "limit": max_req,
                },
            )
    except Exception as e:
        # Fall back to in-memory rate limiter when Redis is unavailable
        from app.dependencies import _in_memory_is_rate_limited

        logger.warning(f"Redis rate limiter unavailable ({e}) — falling back to in-memory limiter")
        key = _get_rate_limit_key(request)
        if _in_memory_is_rate_limited(key, max_requests=max_req, window_seconds=window_sec):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Please slow down and try again later.",
                    "retry_after": window_sec,
                    "limit": max_req,
                },
            )
    return await call_next(request)


# Static files (avatars)
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    checks = {}
    healthy = True

    # Database check
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            break
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # Qdrant check
    try:
        qdrant = get_qdrant_client()
        qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"unavailable: {e}"

    # Redis check
    try:
        limiter = await rate_limiter()
        r = await limiter._get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"unavailable: {e}"

    status = "healthy" if healthy else "degraded"
    return {
        "status": status,
        "service": settings.app_name,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
