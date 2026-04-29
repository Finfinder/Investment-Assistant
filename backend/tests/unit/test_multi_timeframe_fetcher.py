from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.multi_timeframe import MultiTimeframeFetcher
from app.modules.data_acquisition.timeframes import DataTimeframe, resolve_analysis_timeframes


def _make_candles(n: int = 3) -> list[OHLCVData]:
    return [
        OHLCVData(
            timestamp=datetime(2024, 1, 1, hour=index, tzinfo=UTC),
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.5 + index,
            volume=1000.0 + index,
        )
        for index in range(n)
    ]


@pytest.mark.asyncio
async def test_fetch_uses_deduplicated_timeframe_plan_in_order() -> None:
    fetcher = MultiTimeframeFetcher(chain=MagicMock(), session_factory=MagicMock())
    plan = resolve_analysis_timeframes(Timeframe.H1)
    calls: list[DataTimeframe] = []

    async def fake_fetch(symbol: str, timeframe: DataTimeframe, period: str) -> list[OHLCVData]:
        assert symbol == "EURUSD"
        assert period == "200d"
        calls.append(timeframe)
        return _make_candles()

    with patch.object(fetcher, "_fetch_single_timeframe", side_effect=fake_fetch):
        bundle = await fetcher.fetch("EURUSD", plan)

    assert calls == [DataTimeframe.H1, DataTimeframe.D1, DataTimeframe.W1, DataTimeframe.M15]
    assert bundle.main_timeframe == DataTimeframe.H1
    assert len(bundle.main_ohlcv) == 3
    assert bundle.errors == {}


@pytest.mark.asyncio
async def test_fetch_degrades_auxiliary_timeframe_failures() -> None:
    fetcher = MultiTimeframeFetcher(chain=MagicMock(), session_factory=MagicMock())
    plan = resolve_analysis_timeframes(Timeframe.H4)

    async def fake_fetch(_symbol: str, timeframe: DataTimeframe, _period: str) -> list[OHLCVData]:
        if timeframe == DataTimeframe.W1:
            raise RuntimeError("weekly unavailable")
        return _make_candles()

    with patch.object(fetcher, "_fetch_single_timeframe", side_effect=fake_fetch):
        bundle = await fetcher.fetch("EURUSD", plan)

    assert len(bundle.get(DataTimeframe.H4)) == 3
    assert bundle.get(DataTimeframe.W1) == []
    assert bundle.errors == {DataTimeframe.W1: "weekly unavailable"}


@pytest.mark.asyncio
async def test_fetch_raises_when_main_timeframe_fails() -> None:
    fetcher = MultiTimeframeFetcher(chain=MagicMock(), session_factory=MagicMock())
    plan = resolve_analysis_timeframes(Timeframe.M15)

    async def fake_fetch(_symbol: str, timeframe: DataTimeframe, _period: str) -> list[OHLCVData]:
        if timeframe == DataTimeframe.M15:
            raise RuntimeError("main unavailable")
        return _make_candles()

    with (
        patch.object(fetcher, "_fetch_single_timeframe", side_effect=fake_fetch),
        pytest.raises(RuntimeError, match="main unavailable"),
    ):
        await fetcher.fetch("EURUSD", plan)
