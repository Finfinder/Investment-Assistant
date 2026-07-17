"""Shared test helpers."""

from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.models import OHLCVData
from app.main import create_app


def make_ohlcv(
    open_: float,
    high: float,
    low: float,
    close: float,
    index: int = 0,
    volume: float = 1000.0,
) -> OHLCVData:
    """Create a single OHLCVData instance with deterministic timestamp."""
    return OHLCVData(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=index),
        open=round(open_, 4),
        high=round(high, 4),
        low=round(low, 4),
        close=round(close, 4),
        volume=volume,
    )


@contextmanager
def make_app(debug: bool) -> FastAPI:
    """Yield a fresh FastAPI app with ``DEBUG`` overridden via patched settings.

    The settings patch stays active for the whole lifetime of the context
    manager (including app startup/lifespan), so the app always observes the
    intended ``DEBUG`` value instead of reading real settings again.

    Uses pydantic ``model_copy`` instead of copying instance attributes through
    ``setattr``/``dir()``, which avoids the ``PydanticDeprecatedSince211`` warnings
    emitted when mirroring a ``BaseSettings`` instance field-by-field.
    """
    get_settings.cache_clear()
    settings = get_settings().model_copy(update={"DEBUG": debug})
    with patch("app.main.get_settings", return_value=settings):
        yield create_app()


@asynccontextmanager
async def make_client(debug: bool = True) -> AsyncClient:
    """Yield an ``AsyncClient`` bound to a fresh app with ``DEBUG`` overridden.

    The settings patch remains active across the app lifespan (startup) and the
    entire test request cycle, preventing the app from reading real settings
    when ``lifespan()`` calls ``get_settings()`` during startup.
    """
    get_settings.cache_clear()
    settings = get_settings().model_copy(update={"DEBUG": debug})
    with patch("app.main.get_settings", return_value=settings):
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
