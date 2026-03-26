"""Integration tests for fundamental analysis REST API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestFundamentalEndpointForex:
    async def test_post_forex_analysis(self, client):
        mock_fred = MagicMock()
        mock_fred.fetch_indicator = AsyncMock(side_effect=lambda name: {
            "ecb_rate": 4.0,
            "fed_funds_rate": 5.25,
            "cpi_eu": 110.0,
            "cpi_us": 305.0,
        }.get(name))

        with patch(
            "app.modules.fundamental_analysis.forex.FredSource",
            return_value=mock_fred,
        ):
            resp = await client.post(
                "/api/v1/fundamental-analysis",
                json={"symbol": "EURUSD"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["instrument_type"] == "forex"
        assert "score" in data
        assert -100 <= data["score"] <= 100


class TestFundamentalEndpointInvalidSymbol:
    async def test_post_unrecognized_symbol(self, client):
        resp = await client.post(
            "/api/v1/fundamental-analysis",
            json={"symbol": "???"},
        )
        assert resp.status_code == 400
        assert "Nierozpoznany" in resp.json()["detail"]
