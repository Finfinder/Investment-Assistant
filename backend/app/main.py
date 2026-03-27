import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.rate_limit import limiter


def create_app() -> FastAPI:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    # Log available API keys (names only, never values)
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
        logger.info("Configured API keys: %s", ", ".join(configured_keys))
    else:
        logger.warning("No optional API keys configured — only yfinance provider available")

    from app.api.v1.analysis import router as analysis_router
    from app.api.v1.fundamental import router as fundamental_router
    from app.api.v1.health import router as health_router
    from app.api.v1.market_data import router as market_data_router
    from app.api.v1.patterns import router as patterns_router
    from app.api.v1.technical_analysis import router as ta_router

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    app.include_router(market_data_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ta_router, prefix=settings.API_V1_PREFIX)
    app.include_router(patterns_router, prefix=settings.API_V1_PREFIX)
    app.include_router(fundamental_router, prefix=settings.API_V1_PREFIX)
    app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
