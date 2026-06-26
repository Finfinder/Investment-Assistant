"""Health check endpoints for monitoring application and dependency state."""

import logging
import time
from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_start_time = time.monotonic()
try:
    _APP_VERSION = version("investment-assistant")
except PackageNotFoundError:
    _APP_VERSION = "dev"
    logger.debug("Package 'investment-assistant' not installed - using 'dev' version fallback")


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


class DependencyStatus(BaseModel):
    database: str
    redis: str
    yfinance: str
    twelve_data: str
    fmp: str
    fred: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=_APP_VERSION,
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.get("/health/dependencies", response_model=DependencyStatus)
async def health_dependencies() -> DependencyStatus:
    """Check connectivity / availability of external dependencies."""
    db_status = await _check_database()
    redis_status = await _check_redis()
    yfinance_status = _check_yfinance()
    settings = get_settings()

    return DependencyStatus(
        database=db_status,
        redis=redis_status,
        yfinance=yfinance_status,
        twelve_data="configured" if settings.TWELVE_DATA_API_KEY else "not_configured",
        fmp="configured" if settings.FMP_API_KEY else "not_configured",
        fred="configured" if settings.FRED_API_KEY else "not_configured",
    )


async def _check_database() -> str:
    try:
        from sqlalchemy import text

        from app.core.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


def _check_yfinance() -> str:
    try:
        import yfinance  # noqa: F401

        return "ok"
    except ImportError:
        return "error"


async def _check_redis() -> str:
    try:
        from app.core.redis import redis_manager

        if await redis_manager.health_check():
            return "ok"
        return "error"
    except Exception:
        return "not_configured"
