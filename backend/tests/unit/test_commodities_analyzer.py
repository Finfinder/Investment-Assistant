"""Tests for Commodities fundamental analyzer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.models import InstrumentType
from app.modules.fundamental_analysis.commodities import analyze_commodity
from app.modules.fundamental_analysis.data_sources.fmp_source import FmpEconomicSource
from app.modules.fundamental_analysis.data_sources.fred_source import FredSource


@pytest.fixture
def mock_fred():
    fred = MagicMock(spec=FredSource)
    fred.fetch_indicator = AsyncMock(
        side_effect=lambda name: {
            "fed_funds_rate": 5.25,
            "cpi_us": 2.4,
        }.get(name)
    )
    return fred


@pytest.fixture
def mock_fmp():
    return MagicMock(spec=FmpEconomicSource)


class TestCommodityBullish:
    """Large net long speculative + low rates -> bullish."""

    async def test_bullish_gold(self, mock_fred: MagicMock, mock_fmp: MagicMock):
        mock_fmp.fetch_cot_report = AsyncMock(
            return_value={
                "date": "2024-01-15",
                "net_non_commercial": 100000,
                "non_commercial_long": 200000,
                "non_commercial_short": 100000,
                "net_commercial": -50000,
                "net_non_commercial_change": 10000,
            }
        )
        mock_fred.fetch_indicator = AsyncMock(
            side_effect=lambda name: {
                "fed_funds_rate": 1.5,
                "cpi_us": 3.5,
            }.get(name)
        )

        result = await analyze_commodity("GOLD", fred=mock_fred, fmp=mock_fmp)

        assert result.instrument_type == InstrumentType.COMMODITY
        assert result.score > 0  # bullish
        assert "bycza" in result.summary


class TestCommodityBearish:
    """Net short speculative + strong USD -> bearish."""

    async def test_bearish_oil(self, mock_fred: MagicMock, mock_fmp: MagicMock):
        mock_fmp.fetch_cot_report = AsyncMock(
            return_value={
                "date": "2024-01-15",
                "net_non_commercial": -80000,
                "non_commercial_long": 60000,
                "non_commercial_short": 140000,
                "net_commercial": 50000,
                "net_non_commercial_change": -20000,
            }
        )
        mock_fred.fetch_indicator = AsyncMock(
            side_effect=lambda name: {
                "fed_funds_rate": 6.0,
                "cpi_us": 1.5,
            }.get(name)
        )

        result = await analyze_commodity("OIL", fred=mock_fred, fmp=mock_fmp)

        assert result.score < 0
        assert "niedzwiedzia" in result.summary


class TestCommodityNoCotData:
    """Missing COT data should still produce a result."""

    async def test_no_cot_data(self, mock_fred: MagicMock, mock_fmp: MagicMock):
        mock_fmp.fetch_cot_report = AsyncMock(return_value=None)

        result = await analyze_commodity("SILVER", fred=mock_fred, fmp=mock_fmp)

        assert result.instrument_type == InstrumentType.COMMODITY
        assert isinstance(result.score, float)
        assert "Brak danych COT" in result.summary
