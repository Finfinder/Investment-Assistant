"""Shared test helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

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


def make_app(debug: bool):
    """Build a fresh FastAPI app with ``DEBUG`` overridden via patched settings.

    Uses pydantic ``model_copy`` instead of copying instance attributes through
    ``setattr``/``dir()``, which avoids the ``PydanticDeprecatedSince211`` warnings
    emitted when mirroring a ``BaseSettings`` instance field-by-field.
    """
    get_settings.cache_clear()
    settings = get_settings().model_copy(update={"DEBUG": debug})
    with patch("app.main.get_settings", return_value=settings):
        return create_app()
