"""Integration tests for fundamental analysis REST API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestFundamentalEndpointForex:
    async def test_post_forex_analysis(self, client):
        mock_fred = MagicMock()
        mock_fred.fetch_indicator = AsyncMock(
            side_effect=lambda name: {
                "ecb_rate": 4.0,
                "fed_funds_rate": 5.25,
                "cpi_eu": 1.9,
                "cpi_us": 2.4,
            }.get(name)
        )

        with patch(
            "app.modules.fundamental_analysis.forex.MacroDataSource",
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


class TestFundamentalEndpointIndex:
    async def test_post_w20_analysis(self, client):
        mock_fred = MagicMock()
        mock_fred.fetch_indicator = AsyncMock(
            side_effect=lambda name: {
                "pl_rate": 1.0,
                "cpi_pl": 2.0,
                "unemployment_pl": 3.5,
                "gdp_pl": 900000.0,
            }.get(name)
        )

        with patch(
            "app.modules.fundamental_analysis.indices.MacroDataSource",
            return_value=mock_fred,
        ):
            resp = await client.post(
                "/api/v1/fundamental-analysis",
                json={"symbol": "W20"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["instrument_type"] == "index"
        assert data["indicators"]["region"] == "PL"
        assert "Nieznany" not in data["summary"]


class TestFundamentalEndpointInvalidSymbol:
    async def test_post_unrecognized_symbol(self, client):
        resp = await client.post(
            "/api/v1/fundamental-analysis",
            json={"symbol": "???"},
        )
        assert resp.status_code == 400
        assert "Invalid symbol format" in resp.json()["error"]

    async def test_post_valid_but_unrecognized_symbol(self, client):
        resp = await client.post(
            "/api/v1/fundamental-analysis",
            json={"symbol": "ZZZZZ"},
        )
        assert resp.status_code == 400
        assert "Nierozpoznany" in resp.json()["error"]
