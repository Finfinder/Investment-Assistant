from unittest.mock import AsyncMock, patch

import pytest


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
