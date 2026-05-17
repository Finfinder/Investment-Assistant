"""Tests for CPI fallback orchestration."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.fundamental_analysis.data_sources.cpi_fallback_source import CpiFallbackSource
from app.modules.fundamental_analysis.data_sources.macro_observation import MacroObservation


@pytest.fixture
def mock_fred():
    mock = MagicMock()
    mock.fetch_indicator_observation = AsyncMock()
    return mock


@pytest.fixture
def mock_bls():
    mock = MagicMock()
    mock.fetch_us_cpi_yoy = AsyncMock()
    return mock


@pytest.fixture
def mock_statcan():
    mock = MagicMock()
    mock.fetch_ca_cpi_yoy = AsyncMock()
    return mock


@pytest.fixture
def mock_bfs():
    mock = MagicMock()
    mock.fetch_ch_cpi_yoy = AsyncMock()
    return mock


class TestCpiFallbackSource:
    @pytest.mark.asyncio
    async def test_uses_fred_when_observation_is_fresh(
        self,
        mock_fred: MagicMock,
        mock_bls: MagicMock,
        mock_statcan: MagicMock,
        mock_bfs: MagicMock,
    ):
        source = CpiFallbackSource(fred=mock_fred, bls=mock_bls, statcan=mock_statcan, bfs=mock_bfs)
        mock_fred.fetch_indicator_observation.return_value = MacroObservation(
            value=2.2,
            period=date(2026, 4, 1),
            source="fred",
        )

        value = await source.fetch_indicator("cpi_us")

        assert value == pytest.approx(2.2)
        mock_bls.fetch_us_cpi_yoy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_country_source_when_fred_is_stale(
        self,
        mock_fred: MagicMock,
        mock_bls: MagicMock,
        mock_statcan: MagicMock,
        mock_bfs: MagicMock,
    ):
        source = CpiFallbackSource(fred=mock_fred, bls=mock_bls, statcan=mock_statcan, bfs=mock_bfs)
        mock_fred.fetch_indicator_observation.return_value = MacroObservation(
            value=2.2,
            period=date(2025, 1, 1),
            source="fred",
        )
        mock_bls.fetch_us_cpi_yoy.return_value = MacroObservation(value=2.9, period=date(2026, 4, 1), source="bls")

        value = await source.fetch_indicator("cpi_us")

        assert value == pytest.approx(2.9)
        mock_bls.fetch_us_cpi_yoy.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_both_sources_missing(
        self,
        mock_fred: MagicMock,
        mock_bls: MagicMock,
        mock_statcan: MagicMock,
        mock_bfs: MagicMock,
    ):
        source = CpiFallbackSource(fred=mock_fred, bls=mock_bls, statcan=mock_statcan, bfs=mock_bfs)
        mock_fred.fetch_indicator_observation.return_value = None
        mock_bls.fetch_us_cpi_yoy.return_value = None

        value = await source.fetch_indicator("cpi_us")

        assert value is None

    @pytest.mark.asyncio
    async def test_routes_cpi_ca_and_cpi_ch_to_matching_sources(
        self,
        mock_fred: MagicMock,
        mock_bls: MagicMock,
        mock_statcan: MagicMock,
        mock_bfs: MagicMock,
    ):
        source = CpiFallbackSource(fred=mock_fred, bls=mock_bls, statcan=mock_statcan, bfs=mock_bfs)
        mock_fred.fetch_indicator_observation.return_value = None
        mock_statcan.fetch_ca_cpi_yoy.return_value = MacroObservation(
            value=2.1, period=date(2026, 4, 1), source="statcan"
        )
        mock_bfs.fetch_ch_cpi_yoy.return_value = MacroObservation(value=0.7, period=date(2026, 4, 1), source="bfs")

        ca_value = await source.fetch_indicator("cpi_ca")
        ch_value = await source.fetch_indicator("cpi_ch")

        assert ca_value == pytest.approx(2.1)
        assert ch_value == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_fetch_multiple_collects_values(
        self,
        mock_fred: MagicMock,
        mock_bls: MagicMock,
        mock_statcan: MagicMock,
        mock_bfs: MagicMock,
    ):
        source = CpiFallbackSource(fred=mock_fred, bls=mock_bls, statcan=mock_statcan, bfs=mock_bfs)
        mock_fred.fetch_indicator_observation.return_value = None
        mock_bls.fetch_us_cpi_yoy.return_value = MacroObservation(value=2.5, period=date(2026, 4, 1), source="bls")
        mock_statcan.fetch_ca_cpi_yoy.return_value = MacroObservation(
            value=2.0, period=date(2026, 4, 1), source="statcan"
        )

        result = await source.fetch_multiple(["cpi_us", "cpi_ca", "unknown"])

        assert result["cpi_us"] == pytest.approx(2.5)
        assert result["cpi_ca"] == pytest.approx(2.0)
        assert result["unknown"] is None
