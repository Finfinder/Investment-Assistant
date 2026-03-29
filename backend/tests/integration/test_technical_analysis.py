from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.models import OHLCVData


@pytest.fixture
def mock_chain(sample_ohlcv_data_long):
    chain = AsyncMock()
    chain.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data_long)
    return chain


@pytest.mark.asyncio
async def test_technical_analysis_success(client, mock_chain):
    with patch("app.api.v1.technical_analysis.get_fallback_chain", return_value=mock_chain):
        resp = await client.post(
            "/api/v1/technical-analysis",
            json={"symbol": "EURUSD", "timeframe": "H1", "period": "90d"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "EURUSD"
    assert data["timeframe"] == "H1"
    assert len(data["indicators"]) == 13
    assert len(data["moving_averages"]) == 6
    assert len(data["pivot_points"]) == 5
    assert "overall_summary" in data["summary"]


@pytest.mark.asyncio
async def test_technical_analysis_invalid_symbol(client):
    resp = await client.post(
        "/api/v1/technical-analysis",
        json={"symbol": "!!!bad", "timeframe": "H1"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_technical_analysis_no_data(client):
    chain = AsyncMock()
    chain.fetch_ohlcv = AsyncMock(return_value=[])
    with patch("app.api.v1.technical_analysis.get_fallback_chain", return_value=chain):
        resp = await client.post(
            "/api/v1/technical-analysis",
            json={"symbol": "EURUSD", "timeframe": "D1"},
        )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pivot_points_use_daily_candle(client, sample_ohlcv_data_long):
    """Pivot points should have diversified S/R levels when D1 candle has a wide range."""
    # Intraday data: narrow range per candle (simulates H1)
    intraday_data = sample_ohlcv_data_long

    # Daily data: wide price range (simulates real daily candle)
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    daily_data = [
        OHLCVData(
            timestamp=base_time + timedelta(days=i),
            open=round(100.0 + i * 0.5, 2),
            high=round(105.0 + i * 0.5, 2),
            low=round(95.0 + i * 0.5, 2),
            close=round(102.0 + i * 0.5, 2),
            volume=50000.0,
        )
        for i in range(5)
    ]

    chain = AsyncMock()

    async def _side_effect(symbol, timeframe, period):
        if timeframe.value == "D1":
            return daily_data
        return intraday_data

    chain.fetch_ohlcv = AsyncMock(side_effect=_side_effect)

    with patch("app.api.v1.technical_analysis.get_fallback_chain", return_value=chain):
        resp = await client.post(
            "/api/v1/technical-analysis",
            json={"symbol": "EURUSD", "timeframe": "H1", "period": "90d"},
        )

    assert resp.status_code == 200
    data = resp.json()
    pivot_points = data["pivot_points"]
    assert len(pivot_points) == 5

    # Classic pivot points must be strictly ordered: S3 < S2 < S1 < PP < R1 < R2 < R3
    classic = next(p for p in pivot_points if p["type"] == "classic")
    assert classic["s3"] < classic["s2"] < classic["s1"] < classic["pp"] < classic["r1"] < classic["r2"] < classic["r3"]

    # All pivot types must have non-degenerate values (not all same)
    for pp in pivot_points:
        values = [
            v
            for v in [pp.get("s3"), pp.get("s2"), pp.get("s1"), pp["pp"], pp.get("r1"), pp.get("r2"), pp.get("r3")]
            if v is not None
        ]
        assert len(set(values)) > 1, f"Degenerate pivot points for type {pp['type']}"
