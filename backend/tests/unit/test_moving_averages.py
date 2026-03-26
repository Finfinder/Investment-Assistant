from datetime import UTC, datetime, timedelta

from app.core.models import OHLCVData, SignalType
from app.modules.technical_analysis.moving_averages import MA_PERIODS, calculate_moving_averages


def test_returns_6_periods(sample_ohlcv_data_long):
    result = calculate_moving_averages(sample_ohlcv_data_long)
    assert len(result) == 6
    assert [ma.period for ma in result] == list(MA_PERIODS)


def test_short_period_values(sample_ohlcv_data_long):
    """SMA(5) and EMA(5) should have valid values with 250 candles."""
    result = calculate_moving_averages(sample_ohlcv_data_long)
    ma5 = result[0]
    assert ma5.period == 5
    assert ma5.sma_value is not None
    assert ma5.ema_value is not None


def test_long_period_values(sample_ohlcv_data_long):
    """SMA(200) and EMA(200) should have values with 250 candles."""
    result = calculate_moving_averages(sample_ohlcv_data_long)
    ma200 = result[5]
    assert ma200.period == 200
    assert ma200.sma_value is not None
    assert ma200.ema_value is not None


def test_signal_buy_when_close_above_ma():
    """If close is well above MAs, signals should be BUY."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    # Steady uptrend ending at a high price
    data = [
        OHLCVData(timestamp=base + timedelta(hours=i), open=50 + i, high=52 + i, low=49 + i, close=51 + i, volume=1000)
        for i in range(30)
    ]
    result = calculate_moving_averages(data)
    ma5 = result[0]
    # Last close is 80, SMA(5) of last 5 closes (~77), so close > SMA → buy
    assert ma5.sma_signal == SignalType.BUY
    assert ma5.ema_signal == SignalType.BUY


def test_signal_sell_when_close_below_ma():
    """If close is well below MAs, signals should be SELL."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    # Steady downtrend
    data = [
        OHLCVData(
            timestamp=base + timedelta(hours=i), open=200 - i, high=202 - i, low=199 - i, close=201 - i, volume=1000
        )
        for i in range(30)
    ]
    result = calculate_moving_averages(data)
    ma5 = result[0]
    assert ma5.sma_signal == SignalType.SELL
    assert ma5.ema_signal == SignalType.SELL


def test_insufficient_data_returns_none():
    """SMA(200) should be None when only 30 candles are provided."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    data = [
        OHLCVData(timestamp=base + timedelta(hours=i), open=100, high=102, low=99, close=101, volume=1000)
        for i in range(30)
    ]
    result = calculate_moving_averages(data)
    ma200 = result[5]
    assert ma200.sma_value is None
    assert ma200.sma_signal == SignalType.NEUTRAL


def test_empty_input():
    assert calculate_moving_averages([]) == []
