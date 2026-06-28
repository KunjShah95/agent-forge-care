import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import init_db, close_db, get_db
from app.api.router import router as api_router
from app.middleware.auth import RequestLogMiddleware
from app.memory.qdrant_client import init_collections, get_qdrant_client
from app.dependencies import rate_limiter, _get_rate_limit_key
from app.tasks.memory_cleanup import cleanup_expired_memory
from app.tasks.hackathon_scanner import run_scheduled_hackathon_scan

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter() if not settings.debug else logging.Formatter("%(asctime)s | %(name)-12s | %(levelname)-5s | %(message)s"))
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    handlers=[handler],
)
logger = logging.getLogger("agentforge")


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


# Security middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["agentforge.ai", "www.agentforge.ai"]
    )
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
    response.headers["Content-Security-Policy"] = "default-src 'self';"
    
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = "100"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.debug:
        return await call_next(request)
    try:
        limiter = await rate_limiter()
        key = _get_rate_limit_key(request)
        if await limiter.is_rate_limited(key, max_requests=settings.rate_limit_per_minute, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Please slow down and try again later.",
                    "retry_after": 60,
                    "limit": settings.rate_limit_per_minute,
                },
            )
    except Exception:
        logger.warning("Rate limiter unavailable (Redis down?) — allowing request")
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
    return {"status": status, "service": settings.app_name, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}
