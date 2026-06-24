from fastapi import FastAPI, Request, status
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.config import get_settings
from app.api.v1.router import api_router
from app.core.middleware import LoggingAndTimingMiddleware
from app.core.exceptions import RateLimitException, AuthorizationException, EntityNotFoundException

settings = get_settings()
logger = structlog.get_logger()

# ── Logger Setup ──────────────────────────────────────────────────
# Since we are using structlog, we'll let Uvicorn handle stdout while we write JSON-formatted log outputs.
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20), # INFO
    cache_logger_on_first_use=True,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", version=settings.APP_VERSION, debug=settings.DEBUG)
    yield
    logger.info("app_shutting_down")

# ── App Setup ─────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Timing & Timing Middleware
app.add_middleware(LoggingAndTimingMiddleware)

# Include main API router
app.include_router(api_router, prefix="/api/v1")

# ── Exception Handlers ────────────────────────────────────────────

@app.exception_handler(RateLimitException)
async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    logger.warning("rate_limit_exceeded", path=request.url.path, ip=request.client.host if request.client else "unknown")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.detail}
    )

@app.exception_handler(AuthorizationException)
async def authorization_exception_handler(request: Request, exc: AuthorizationException):
    logger.warning("authorization_denied", path=request.url.path, ip=request.client.host if request.client else "unknown")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail}
    )

@app.exception_handler(EntityNotFoundException)
async def entity_not_found_exception_handler(request: Request, exc: EntityNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_error", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please contact support."}
    )

# Hooks managed by lifespan context manager above
