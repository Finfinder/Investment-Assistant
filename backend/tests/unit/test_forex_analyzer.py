"""Tests for Forex fundamental analyzer."""

from unittest.mock import MagicMock

import pytest

from app.core.models import InstrumentType
from app.modules.fundamental_analysis.data_sources.fred_source import FredSource
from app.modules.fundamental_analysis.forex import _parse_pair, analyze_forex


@pytest.fixture
def mock_fred():
    return MagicMock(spec=FredSource)


class TestParsePair:
    def test_parse_standard_pair(self):
        assert _parse_pair("EURUSD") == ("EUR", "USD")

    def test_parse_pair_with_slash(self):
        assert _parse_pair("EUR/USD") == ("EUR", "USD")

    def test_parse_unknown_6char(self):
        base, quote = _parse_pair("ABCDEF")
        assert base == "ABC"
        assert quote == "DEF"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _parse_pair("X")


class TestForexAnalyzerEurStronger:
    """EUR has higher rates and lower inflation -> bullish EURUSD."""

    def test_eur_stronger_than_usd(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 4.5,
            "fed_funds_rate": 2.0,
            "cpi_eu": 100.0,
            "cpi_us": 105.0,
        }.get(name)

        result = analyze_forex("EURUSD", fred=mock_fred)

        assert result.instrument_type == InstrumentType.FOREX
        assert result.score > 0  # bullish for EUR
        assert result.indicators["interest_rate_differential"] == 2.5
        assert "bycza" in result.summary


class TestForexAnalyzerUsdStronger:
    """USD has higher rates -> bearish EURUSD."""

    def test_usd_stronger_than_eur(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 1.0,
            "fed_funds_rate": 5.5,
            "cpi_eu": 103.0,
            "cpi_us": 100.0,
        }.get(name)

        result = analyze_forex("EURUSD", fred=mock_fred)

        assert result.score < 0  # bearish for pair
        assert result.indicators["interest_rate_differential"] == -4.5
        assert "niedzwiedzia" in result.summary


class TestForexAnalyzerBalanced:
    """Similar rates and inflation -> neutral."""

    def test_balanced_macro(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 3.0,
            "fed_funds_rate": 3.0,
            "cpi_eu": 102.0,
            "cpi_us": 102.0,
        }.get(name)

        result = analyze_forex("EURUSD", fred=mock_fred)

        assert -10 <= result.score <= 10
        assert "neutralna" in result.summary


class TestForexAnalyzerMissingData:
    """Missing macro data -> score 0, appropriate summary."""

    def test_missing_data_scores_zero(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.return_value = None

        result = analyze_forex("EURUSD", fred=mock_fred)

        assert result.score == 0.0
        assert "Brak danych" in result.summary
