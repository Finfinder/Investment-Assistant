"""Tests for macro source facade routing between OECD and FRED."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.fundamental_analysis.data_sources.macro_source import MacroDataSource


@pytest.fixture
def mock_fred():
    mock = MagicMock()
    mock.fetch_indicator = AsyncMock()
    return mock


@pytest.fixture
def mock_oecd():
    mock = MagicMock()
    mock.fetch_jp_cpi_yoy = AsyncMock()
    return mock


class TestMacroSourceRouting:
    @pytest.mark.asyncio
    async def test_fetch_indicator_routes_cpi_jp_to_oecd(self, mock_fred: MagicMock, mock_oecd: MagicMock):
        mock_oecd.fetch_jp_cpi_yoy.return_value = 2.1
        source = MacroDataSource(fred=mock_fred, oecd=mock_oecd)

        result = await source.fetch_indicator("cpi_jp")

        assert result == pytest.approx(2.1)
        mock_oecd.fetch_jp_cpi_yoy.assert_awaited_once()
        mock_fred.fetch_indicator.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_indicator_routes_non_jp_indicators_to_fred(self, mock_fred: MagicMock, mock_oecd: MagicMock):
        mock_fred.fetch_indicator.return_value = 5.25
        source = MacroDataSource(fred=mock_fred, oecd=mock_oecd)

        result = await source.fetch_indicator("fed_funds_rate")

        assert result == pytest.approx(5.25)
        mock_fred.fetch_indicator.assert_awaited_once_with("fed_funds_rate", 365)
        mock_oecd.fetch_jp_cpi_yoy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_indicator_preserves_none_for_unknown_indicator(
        self, mock_fred: MagicMock, mock_oecd: MagicMock
    ):
        mock_fred.fetch_indicator.return_value = None
        source = MacroDataSource(fred=mock_fred, oecd=mock_oecd)

        result = await source.fetch_indicator("unknown_indicator")

        assert result is None
        mock_fred.fetch_indicator.assert_awaited_once_with("unknown_indicator", 365)
        mock_oecd.fetch_jp_cpi_yoy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_multiple_routes_mixed_indicator_list(self, mock_fred: MagicMock, mock_oecd: MagicMock):
        mock_oecd.fetch_jp_cpi_yoy.return_value = 1.7
        mock_fred.fetch_indicator.side_effect = lambda name, _: {
            "fed_funds_rate": 4.0,
            "boj_rate": 0.1,
        }.get(name)
        source = MacroDataSource(fred=mock_fred, oecd=mock_oecd)

        result = await source.fetch_multiple(["cpi_jp", "fed_funds_rate", "boj_rate"])

        assert result["cpi_jp"] == pytest.approx(1.7)
        assert result["fed_funds_rate"] == pytest.approx(4.0)
        assert result["boj_rate"] == pytest.approx(0.1)
        mock_oecd.fetch_jp_cpi_yoy.assert_awaited_once()
        assert mock_fred.fetch_indicator.await_count == 2
