"""Tests for Indices fundamental analyzer."""

from unittest.mock import MagicMock

import pytest

from app.core.models import InstrumentType
from app.modules.fundamental_analysis.data_sources.fred_source import FredSource
from app.modules.fundamental_analysis.indices import analyze_index


@pytest.fixture
def mock_fred():
    return MagicMock(spec=FredSource)


class TestIndexBullish:
    """Low rates + low unemployment -> bullish for equities."""

    def test_bullish_us500(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 1.0,
            "cpi_us": 290.0,
            "unemployment_us": 3.5,
            "gdp_us": 25000.0,
        }.get(name)

        result = analyze_index("US500", fred=mock_fred)

        assert result.instrument_type == InstrumentType.INDEX
        assert result.score > 0
        assert result.indicators["region"] == "US"
        assert "bycza" in result.summary


class TestIndexBearish:
    """High rates + high unemployment -> bearish."""

    def test_bearish_us500(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 6.5,
            "cpi_us": 320.0,
            "unemployment_us": 8.0,
            "gdp_us": 22000.0,
        }.get(name)

        result = analyze_index("US500", fred=mock_fred)

        assert result.score < 0
        assert "niedzwiedzia" in result.summary


class TestIndexUnknownSymbol:
    """Unknown index symbol -> score 0 with appropriate message."""

    def test_unknown_index(self, mock_fred: MagicMock):
        result = analyze_index("UNKNOWN_INDEX", fred=mock_fred)

        assert result.score == 0.0
        assert "Nieznany" in result.summary
        mock_fred.fetch_indicator.assert_not_called()


class TestIndexEuropean:
    """European index should use ECB indicators."""

    def test_de40_uses_eu_region(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 4.5,
            "cpi_eu": 115.0,
        }.get(name)

        result = analyze_index("DE40", fred=mock_fred)

        assert result.indicators["region"] == "EU"
        assert result.instrument_type == InstrumentType.INDEX
