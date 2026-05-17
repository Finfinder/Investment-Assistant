"""Tests for Forex fundamental analyzer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.models import InstrumentType
from app.modules.fundamental_analysis.data_sources.fred_source import FredSource
from app.modules.fundamental_analysis.forex import _parse_pair, analyze_forex


@pytest.fixture
def mock_fred():
    mock = MagicMock(spec=FredSource)
    mock.fetch_indicator = AsyncMock()
    return mock


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

    @pytest.mark.asyncio
    async def test_eur_stronger_than_usd(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 4.5,
            "fed_funds_rate": 2.0,
            "cpi_eu": 1.5,
            "cpi_us": 3.5,
        }.get(name)

        result = await analyze_forex("EURUSD", fred=mock_fred)

        assert result.instrument_type == InstrumentType.FOREX
        assert result.score > 0  # bullish for EUR
        assert result.indicators["interest_rate_differential"] == pytest.approx(2.5)
        assert result.indicators["inflation_differential"] == pytest.approx(-2.0)
        assert "bycza" in result.summary


class TestForexAnalyzerUsdStronger:
    """USD has higher rates -> bearish EURUSD."""

    @pytest.mark.asyncio
    async def test_usd_stronger_than_eur(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 1.0,
            "fed_funds_rate": 5.5,
            "cpi_eu": 4.0,
            "cpi_us": 2.0,
        }.get(name)

        result = await analyze_forex("EURUSD", fred=mock_fred)

        assert result.score < 0  # bearish for pair
        assert result.indicators["interest_rate_differential"] == pytest.approx(-4.5)
        assert result.indicators["inflation_differential"] == pytest.approx(2.0)
        assert "niedzwiedzia" in result.summary


class TestForexAnalyzerBalanced:
    """Similar rates and inflation -> neutral."""

    @pytest.mark.asyncio
    async def test_balanced_macro(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 3.0,
            "fed_funds_rate": 3.0,
            "cpi_eu": 2.5,
            "cpi_us": 2.5,
        }.get(name)

        result = await analyze_forex("EURUSD", fred=mock_fred)

        assert -10 <= result.score <= 10
        assert result.indicators["inflation_differential"] == pytest.approx(0.0)
        assert "neutralna" in result.summary


class TestForexAnalyzerJpyPairs:
    """JPY pairs should use JP CPI via cpi_jp mapping."""

    @pytest.mark.asyncio
    async def test_usdjpy_uses_jpy_cpi_for_inflation_differential(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 5.0,
            "boj_rate": 0.1,
            "cpi_us": 3.0,
            "cpi_jp": 2.2,
        }.get(name)

        result = await analyze_forex("USDJPY", fred=mock_fred)

        assert result.indicators["USD_inflation_yoy"] == pytest.approx(3.0)
        assert result.indicators["JPY_inflation_yoy"] == pytest.approx(2.2)
        assert result.indicators["inflation_differential"] == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_usdjpy_missing_jpy_cpi_degrades_inflation_component(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 5.0,
            "boj_rate": 0.1,
            "cpi_us": 3.0,
            "cpi_jp": None,
        }.get(name)

        result = await analyze_forex("USDJPY", fred=mock_fred)

        assert result.indicators["USD_inflation_yoy"] == pytest.approx(3.0)
        assert result.indicators["JPY_inflation_yoy"] is None
        assert result.indicators["inflation_differential"] is None
        assert result.score != pytest.approx(0.0)


class TestForexAnalyzerMissingData:
    """Missing macro data -> score 0, appropriate summary."""

    @pytest.mark.asyncio
    async def test_missing_data_scores_zero(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.return_value = None

        result = await analyze_forex("EURUSD", fred=mock_fred)

        assert result.score == pytest.approx(0.0)
        assert "Brak danych" in result.summary
        assert result.indicators["interest_rate_differential"] is None
        assert result.indicators["inflation_differential"] is None


class TestForexAnalyzerCpiRouting:
    @pytest.mark.asyncio
    async def test_usdcad_uses_us_and_ca_cpi_indicators(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 4.5,
            "boc_rate": 3.5,
            "cpi_us": 2.4,
            "cpi_ca": 1.9,
        }.get(name)

        result = await analyze_forex("USDCAD", fred=mock_fred)

        assert result.indicators["USD_inflation_yoy"] == pytest.approx(2.4)
        assert result.indicators["CAD_inflation_yoy"] == pytest.approx(1.9)
        assert result.indicators["inflation_differential"] == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_usdchf_uses_us_and_ch_cpi_indicators(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 4.5,
            "snb_rate": 1.0,
            "cpi_us": 2.4,
            "cpi_ch": 0.7,
        }.get(name)

        result = await analyze_forex("USDCHF", fred=mock_fred)

        assert result.indicators["USD_inflation_yoy"] == pytest.approx(2.4)
        assert result.indicators["CHF_inflation_yoy"] == pytest.approx(0.7)
        assert result.indicators["inflation_differential"] == pytest.approx(1.7)


class TestForexAnalyzerAudnzd:
    """AUDNZD pair with NZD macro data."""

    @pytest.mark.asyncio
    async def test_audnzd_with_both_currencies_data(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "rba_rate": 4.35,
            "rbnz_rate": 5.50,
            "cpi_au": 3.6,
            "cpi_nz": 4.0,
        }.get(name)

        result = await analyze_forex("AUDNZD", fred=mock_fred)

        assert result.instrument_type == InstrumentType.FOREX
        assert result.score != pytest.approx(0.0)
        assert result.indicators["base_currency"] == "AUD"
        assert result.indicators["quote_currency"] == "NZD"
        assert result.indicators["interest_rate_differential"] == pytest.approx(-1.15)
        assert result.indicators["inflation_differential"] == pytest.approx(-0.4)
        assert "AUD/NZD" in result.summary

    @pytest.mark.asyncio
    async def test_audnzd_missing_nzd_data(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "rba_rate": 4.35,
            "rbnz_rate": None,
            "cpi_au": 3.6,
            "cpi_nz": None,
        }.get(name)

        result = await analyze_forex("AUDNZD", fred=mock_fred)

        assert result.instrument_type == InstrumentType.FOREX
        assert result.score == pytest.approx(0.0)
        assert "Brak danych" in result.summary

    @pytest.mark.asyncio
    async def test_audnzd_partial_missing_cpi_base_none(self, mock_fred: MagicMock):
        """AUD CPI missing but NZD CPI available — inflation_differential must be None."""
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "rba_rate": 4.35,
            "rbnz_rate": 5.50,
            "cpi_au": None,
            "cpi_nz": 2.5,
        }.get(name)

        result = await analyze_forex("AUDNZD", fred=mock_fred)

        assert result.indicators["AUD_inflation_yoy"] is None
        assert result.indicators["NZD_inflation_yoy"] == pytest.approx(2.5)
        assert result.indicators["inflation_differential"] is None
        assert result.score != pytest.approx(0.0)  # rate component still contributes
        assert "roznica inflacji" not in result.summary

    @pytest.mark.asyncio
    async def test_audnzd_partial_missing_rate_quote_none(self, mock_fred: MagicMock):
        """RBNZ rate missing but RBA rate available — interest_rate_differential must be None."""
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "rba_rate": 4.35,
            "rbnz_rate": None,
            "cpi_au": 3.6,
            "cpi_nz": 2.5,
        }.get(name)

        result = await analyze_forex("AUDNZD", fred=mock_fred)

        assert result.indicators["interest_rate_differential"] is None
        assert result.indicators["inflation_differential"] == pytest.approx(1.1)
        assert result.score != pytest.approx(0.0)  # inflation component still contributes
        assert "roznica stop" not in result.summary
        assert "roznica inflacji" in result.summary
