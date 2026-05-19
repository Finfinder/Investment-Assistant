"""Tests for Indices fundamental analyzer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.models import InstrumentType
from app.modules.fundamental_analysis.data_sources.fred_source import FredSource
from app.modules.fundamental_analysis.indices import analyze_index


@pytest.fixture
def mock_fred():
    mock = MagicMock(spec=FredSource)
    mock.fetch_indicator = AsyncMock()
    return mock


class TestIndexBullish:
    """Low rates + low unemployment -> bullish for equities."""

    @pytest.mark.asyncio
    async def test_bullish_us500(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 1.0,
            "cpi_us": 2.0,
            "unemployment_us": 3.5,
            "gdp_us": 25000.0,
        }.get(name)

        result = await analyze_index("US500", fred=mock_fred)

        assert result.instrument_type == InstrumentType.INDEX
        assert result.score > 0
        assert result.indicators["region"] == "US"
        assert result.indicators["inflation_yoy"] == pytest.approx(2.0)
        assert "bycza" in result.summary


class TestIndexBearish:
    """High rates + high unemployment -> bearish."""

    @pytest.mark.asyncio
    async def test_bearish_us500(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "fed_funds_rate": 6.5,
            "cpi_us": 5.0,
            "unemployment_us": 8.0,
            "gdp_us": 22000.0,
        }.get(name)

        result = await analyze_index("US500", fred=mock_fred)

        assert result.score < 0
        assert result.indicators["inflation_yoy"] == pytest.approx(5.0)
        assert "niedzwiedzia" in result.summary


class TestIndexUnknownSymbol:
    """Unknown index symbol -> score 0 with appropriate message."""

    @pytest.mark.asyncio
    async def test_unknown_index(self, mock_fred: MagicMock):
        result = await analyze_index("UNKNOWN_INDEX", fred=mock_fred)

        assert result.score == pytest.approx(0.0)
        assert "Nieznany" in result.summary
        mock_fred.fetch_indicator.assert_not_called()


class TestIndexEuropean:
    """European index should use ECB indicators."""

    @pytest.mark.asyncio
    async def test_de40_uses_eu_region(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 4.5,
            "cpi_eu": 1.9,
        }.get(name)

        result = await analyze_index("DE40", fred=mock_fred)

        assert result.indicators["region"] == "EU"
        assert result.instrument_type == InstrumentType.INDEX

    @pytest.mark.asyncio
    async def test_fr40_uses_eu_region(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "ecb_rate": 3.75,
            "cpi_eu": 2.1,
        }.get(name)

        result = await analyze_index("FR40", fred=mock_fred)

        assert result.instrument_type == InstrumentType.INDEX
        assert result.indicators["region"] == "EU"
        assert result.indicators["interest_rate"] == pytest.approx(3.75)
        assert result.indicators["inflation_yoy"] == pytest.approx(2.1)
        assert "Nieznany" not in result.summary


class TestIndexJapanese:
    """JP indices should include cpi_jp in inflation output."""

    @pytest.mark.asyncio
    async def test_jp225_uses_jp_rate_and_cpi(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "boj_rate": 0.1,
            "cpi_jp": 2.4,
        }.get(name)

        result = await analyze_index("JP225", fred=mock_fred)

        assert result.indicators["region"] == "JP"
        assert result.indicators["interest_rate"] == pytest.approx(0.1)
        assert result.indicators["inflation_yoy"] == pytest.approx(2.4)
        assert result.instrument_type == InstrumentType.INDEX

    @pytest.mark.asyncio
    async def test_nikkei_missing_cpi_jp_keeps_analysis_running(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "boj_rate": 0.1,
            "cpi_jp": None,
        }.get(name)

        result = await analyze_index("NIKKEI", fred=mock_fred)

        assert result.indicators["region"] == "JP"
        assert result.indicators["inflation_yoy"] is None
        assert result.score != pytest.approx(0.0)


class TestIndexAustralian:
    """AU indices should include cpi_au in inflation output."""

    @pytest.mark.asyncio
    async def test_au200_uses_au_rate_and_cpi(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "rba_rate": 4.35,
            "cpi_au": 3.16,
        }.get(name)

        result = await analyze_index("AU200", fred=mock_fred)

        assert result.indicators["region"] == "AU"
        assert result.indicators["interest_rate"] == pytest.approx(4.35)
        assert result.indicators["inflation_yoy"] == pytest.approx(3.16)
        assert result.instrument_type == InstrumentType.INDEX


class TestIndexCanadian:
    """CA index should include cpi_ca in inflation output."""

    @pytest.mark.asyncio
    async def test_ca60_uses_ca_rate_and_cpi(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "boc_rate": 4.0,
            "cpi_ca": 2.1,
        }.get(name)

        result = await analyze_index("CA60", fred=mock_fred)

        assert result.indicators["region"] == "CA"
        assert result.indicators["interest_rate"] == pytest.approx(4.0)
        assert result.indicators["inflation_yoy"] == pytest.approx(2.1)
        assert result.instrument_type == InstrumentType.INDEX


class TestIndexPolish:
    """PL index should use Polish macro indicators."""

    @pytest.mark.asyncio
    async def test_w20_uses_pl_region_and_macro_keys(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "pl_rate": 1.0,
            "cpi_pl": 2.0,
            "unemployment_pl": 3.5,
            "gdp_pl": 900000.0,
        }.get(name)

        result = await analyze_index("W20", fred=mock_fred)

        assert result.instrument_type == InstrumentType.INDEX
        assert result.indicators["region"] == "PL"
        assert result.indicators["interest_rate"] == pytest.approx(1.0)
        assert result.indicators["inflation_yoy"] == pytest.approx(2.0)
        assert result.indicators["unemployment"] == pytest.approx(3.5)
        assert result.indicators["gdp"] == pytest.approx(900000.0)
        assert result.score > 0
        assert "Nieznany" not in result.summary

    @pytest.mark.asyncio
    async def test_w20_degrades_when_cpi_pl_is_missing(self, mock_fred: MagicMock):
        mock_fred.fetch_indicator.side_effect = lambda name: {
            "pl_rate": 1.0,
            "cpi_pl": None,
            "unemployment_pl": 3.5,
            "gdp_pl": 900000.0,
        }.get(name)

        result = await analyze_index("W20", fred=mock_fred)

        assert result.instrument_type == InstrumentType.INDEX
        assert result.indicators["region"] == "PL"
        assert result.indicators["inflation_yoy"] is None
        assert "Nieznany" not in result.summary
