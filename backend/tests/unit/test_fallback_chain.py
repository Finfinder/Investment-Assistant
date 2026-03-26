from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.fallback_chain import DataProviderError, FallbackChainManager
from app.modules.data_acquisition.interfaces import DataProviderPriority


def _make_mock_provider(
    name: str,
    priority: DataProviderPriority,
    ohlcv_result: list[OHLCVData] | None = None,
    side_effect: Exception | None = None,
) -> AsyncMock:
    provider = AsyncMock()
    provider.name = name
    provider.priority = priority

    if side_effect:
        provider.fetch_ohlcv = AsyncMock(side_effect=side_effect)
    elif ohlcv_result is not None:
        provider.fetch_ohlcv = AsyncMock(return_value=ohlcv_result)
    else:
        provider.fetch_ohlcv = AsyncMock(return_value=[])

    return provider


_SAMPLE_DATA = [
    OHLCVData(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=1.10,
        high=1.15,
        low=1.05,
        close=1.12,
        volume=1000.0,
    )
]


class TestFallbackChainManager:
    @pytest.mark.asyncio
    async def test_primary_success(self) -> None:
        primary = _make_mock_provider("primary", DataProviderPriority.PRIMARY, _SAMPLE_DATA)
        secondary = _make_mock_provider("secondary", DataProviderPriority.SECONDARY, _SAMPLE_DATA)

        chain = FallbackChainManager([primary, secondary])
        result = await chain.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert len(result) == 1
        primary.fetch_ohlcv.assert_awaited_once()
        secondary.fetch_ohlcv.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_primary_fail_secondary_success(self) -> None:
        primary = _make_mock_provider(
            "primary", DataProviderPriority.PRIMARY, side_effect=RuntimeError("timeout")
        )
        secondary = _make_mock_provider("secondary", DataProviderPriority.SECONDARY, _SAMPLE_DATA)

        chain = FallbackChainManager([secondary, primary])  # order shouldn't matter
        result = await chain.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert len(result) == 1
        primary.fetch_ohlcv.assert_awaited_once()
        secondary.fetch_ohlcv.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_primary_empty_secondary_success(self) -> None:
        primary = _make_mock_provider("primary", DataProviderPriority.PRIMARY, ohlcv_result=[])
        secondary = _make_mock_provider("secondary", DataProviderPriority.SECONDARY, _SAMPLE_DATA)

        chain = FallbackChainManager([primary, secondary])
        result = await chain.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_all_fail_raises(self) -> None:
        primary = _make_mock_provider(
            "primary", DataProviderPriority.PRIMARY, side_effect=RuntimeError("fail1")
        )
        secondary = _make_mock_provider(
            "secondary", DataProviderPriority.SECONDARY, side_effect=RuntimeError("fail2")
        )

        chain = FallbackChainManager([primary, secondary])

        with pytest.raises(DataProviderError, match="All providers failed"):
            await chain.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

    def test_providers_sorted_by_priority(self) -> None:
        secondary = _make_mock_provider("secondary", DataProviderPriority.SECONDARY)
        primary = _make_mock_provider("primary", DataProviderPriority.PRIMARY)
        tertiary = _make_mock_provider("tertiary", DataProviderPriority.TERTIARY)

        chain = FallbackChainManager([tertiary, primary, secondary])
        names = [p.name for p in chain.providers]
        # Sorted alphabetically by priority value: fallback < primary < secondary < tertiary
        assert names[0] == "primary"
