"""Health check endpoints for monitoring application and dependency state.

Usage:
    GET /api/v1/health - Public minimal health check
    GET /api/v1/health/dependencies - Authenticated detailed dependency status
"""

import logging
import time
from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.core.auth import require_auth
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.redis import redis_manager

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


class DependencyStatus(BaseModel):
    database: str
    redis: str
    yfinance: str
    twelve_data: str
    fmp: str
    fred: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Public health check returning minimal status.

    Returns a simple OK status without exposing sensitive information
    like version numbers or uptime that could aid attackers in reconnaissance.
    """
    return HealthResponse(status="ok")


@router.get("/health/dependencies", response_model=DependencyStatus)
async def health_dependencies(user: str = Depends(require_auth)) -> DependencyStatus:
    """Check connectivity / availability of external dependencies.

    Requires authentication. Provides detailed status of external API keys
    and dependencies for diagnostic purposes.

    Args:
        user: Authenticated user (injected via require_auth dependency)

    Returns:
        DependencyStatus with detailed status of all dependencies
    """
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
    """Check database connectivity.

    Returns:
        "ok" if database connection is working, "error" otherwise.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"), timeout=5)
        return "ok"
    except Exception:
        return "error"


def _check_yfinance() -> str:
    """Check if yfinance library is available.

    Returns:
        "ok" if yfinance is installed, "error" otherwise.
    """
    try:
        import yfinance  # noqa: F401

        return "ok"
    except ImportError:
        return "error"


async def _check_redis() -> str:
    """Check Redis connectivity.

    Returns:
        "ok" if Redis connection is working, "error" on failure,
        "not_configured" if Redis is not configured.
    """
    try:
        if await redis_manager.health_check():
            return "ok"
        return "error"
    except Exception:
        return "not_configured"
