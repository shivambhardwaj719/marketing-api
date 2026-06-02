from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import check_db_connection, close_db
from app.core.logger import get_logger, setup_logging
from app.core.middleware import (
    ExceptionHandlerMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

setup_logging()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION, env=settings.APP_ENV)

    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("database_unavailable_on_startup")
    else:
        logger.info("database_connected")

    yield

    await close_db()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade FastAPI backend for Facebook Lead Ads CRM "
        "and Campaign Management Platform."
    ),
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware (order matters: outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


# Routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


# Health endpoints
@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check():
    db_ok = await check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
        "version": settings.APP_VERSION,
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}


# Paths that do NOT require a Bearer token in Swagger
_PUBLIC_PATHS: set[str] = {
    f"{settings.API_V1_PREFIX}/auth/register",
    f"{settings.API_V1_PREFIX}/auth/login",
    f"{settings.API_V1_PREFIX}/auth/refresh",
    f"{settings.API_V1_PREFIX}/auth/facebook/login",
    f"{settings.API_V1_PREFIX}/auth/facebook/callback",
    f"{settings.API_V1_PREFIX}/webhooks/facebook",
    "/health",
    "/",
}


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "## FastFacebook CRM — REST API\n\n"
            "### Authentication\n"
            "Most endpoints require a **Bearer JWT token**.\n\n"
            "1. Call `POST /api/v1/auth/login` with your email & password\n"
            "2. Copy the `access_token` from the response\n"
            "3. Click the **Authorize 🔒** button above and paste: `<your_token>`\n"
            "4. All locked endpoints will use it automatically"
        ),
        routes=app.routes,
    )

    # Replace auto-generated HTTPBearer scheme with our named BearerAuth
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your JWT access_token here (no 'Bearer ' prefix needed)",
        }
    }

    for path, path_data in schema.get("paths", {}).items():
        for method, operation in path_data.items():
            if not isinstance(operation, dict):
                continue
            if path in _PUBLIC_PATHS:
                # Public — open padlock, no token required
                operation["security"] = []
            else:
                # Protected — closed padlock, token auto-sent after Authorize
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
