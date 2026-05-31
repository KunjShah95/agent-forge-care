import logging
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db
from app.api.router import router as api_router
from app.middleware.auth import RequestLogMiddleware
from app.memory.qdrant_client import init_collections
from app.dependencies import rate_limiter, _get_rate_limit_key

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s | %(name)-12s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("agentforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting %s...", settings.app_name)
    await init_db()
    logger.info("Database tables created / verified")
    try:
        init_collections()
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.warning("Qdrant init skipped: %s", e)
    yield
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


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.debug:
        return await call_next(request)
    try:
        limiter = await rate_limiter()
        key = _get_rate_limit_key(request)
        if await limiter.is_rate_limited(key, max_requests=100, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
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
    return {"status": "healthy", "service": settings.app_name}
