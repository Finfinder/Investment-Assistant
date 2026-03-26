"""Shared test helpers."""

from datetime import UTC, datetime, timedelta

from app.core.models import OHLCVData


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
