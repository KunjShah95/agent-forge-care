import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.api.router import router as api_router
from app.dependencies import limiter
from app.middleware.auth import RequestLogMiddleware
from app.memory.qdrant_client import init_collections

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
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
    )


# Middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}
