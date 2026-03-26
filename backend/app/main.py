from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
