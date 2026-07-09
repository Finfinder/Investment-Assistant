import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.rate_limit import limiter
from app.core.redis import redis_manager
from app.core.security_headers import SecurityHeadersMiddleware

_lifespan_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage Redis connection lifecycle."""
    settings = get_settings()
    if settings.REDIS_PASSWORD == "" and not settings.DEBUG:
        raise RuntimeError("REDIS_PASSWORD must be configured in production")
    _dev_secret = "dev-secret-key-change-in-production"  # noqa: S105
    if _dev_secret == settings.SECRET_KEY and not settings.DEBUG:
        raise RuntimeError("SECRET_KEY must be configured in production")
    if _dev_secret == settings.SECRET_KEY:
        _lifespan_logger.warning("Using development SECRET_KEY - do not use in production")
    if settings.AUTH_PASSWORD_HASH == "" and not settings.DEBUG:
        raise RuntimeError("AUTH_PASSWORD_HASH must be configured in production")
    await redis_manager.initialize()
    yield
    await redis_manager.close()


def create_app() -> FastAPI:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Correlation ID + centralized, sanitized error responses.
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Security headers (HSTS, CSP, X-Frame-Options, etc.) only in production.
    # In local development (DEBUG=True) they are skipped to avoid breaking hot reload.
    if not settings.DEBUG:
        app.add_middleware(SecurityHeadersMiddleware)

    # Log count of configured API keys (never names or values)
    configured_keys = [
        name
        for name, val in [
            ("TWELVE_DATA_API_KEY", settings.TWELVE_DATA_API_KEY),
            ("FMP_API_KEY", settings.FMP_API_KEY),
            ("FRED_API_KEY", settings.FRED_API_KEY),
        ]
        if val
    ]
    if configured_keys:
        logger.info("Configured %d optional API key(s)", len(configured_keys))
    else:
        logger.warning("No optional API keys configured - only yfinance provider available")

    from app.api.v1.analysis import router as analysis_router
    from app.api.v1.auth import router as auth_router
    from app.api.v1.fundamental import router as fundamental_router
    from app.api.v1.health import router as health_router
    from app.api.v1.market_data import router as market_data_router
    from app.api.v1.patterns import router as patterns_router
    from app.api.v1.technical_analysis import router as ta_router

    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    app.include_router(market_data_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ta_router, prefix=settings.API_V1_PREFIX)
    app.include_router(patterns_router, prefix=settings.API_V1_PREFIX)
    app.include_router(fundamental_router, prefix=settings.API_V1_PREFIX)
    app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
