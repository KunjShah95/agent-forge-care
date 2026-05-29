import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.api.router import router as api_router
from app.middleware.auth import RequestLogMiddleware

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

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}
