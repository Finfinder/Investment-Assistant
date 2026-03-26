from app.core.models import OHLCVData, SignalType
from app.modules.technical_analysis.indicators import calculate_indicators

EXPECTED_NAMES = [
    "RSI(14)",
    "STOCH.K(14)",
    "CCI(20)",
    "ADX(14)",
    "AO",
    "Momentum(10)",
    "MACD(12,26,9)",
    "Williams %R(14)",
    "UO(7,14,28)",
]


def test_returns_9_indicators(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    assert len(result) == 9


def test_indicator_names(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    names = [r.name for r in result]
    assert names == EXPECTED_NAMES


def test_all_have_values(sample_ohlcv_data_long):
    """With 250 candles, all indicators should produce non-None values."""
    result = calculate_indicators(sample_ohlcv_data_long)
    for ind in result:
        assert ind.value is not None, f"{ind.name} has None value"


def test_rsi_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    rsi = next(r for r in result if r.name == "RSI(14)")
    assert 0.0 <= rsi.value <= 100.0


def test_stochastic_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    stoch = next(r for r in result if r.name == "STOCH.K(14)")
    assert 0.0 <= stoch.value <= 100.0


def test_williams_r_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    willr = next(r for r in result if r.name == "Williams %R(14)")
    assert -100.0 <= willr.value <= 0.0


def test_uo_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    uo = next(r for r in result if r.name == "UO(7,14,28)")
    assert 0.0 <= uo.value <= 100.0


def test_signals_are_valid(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long)
    valid = set(SignalType)
    for ind in result:
        assert ind.signal in valid, f"{ind.name} has invalid signal {ind.signal}"


def test_empty_input():
    assert calculate_indicators([]) == []


def test_single_candle():
    from datetime import UTC, datetime

    candle = OHLCVData(timestamp=datetime(2024, 1, 1, tzinfo=UTC), open=100, high=102, low=99, close=101, volume=1000)
    assert calculate_indicators([candle]) == []


def test_short_data_returns_none_values(sample_ohlcv_data):
    """With only 20 candles, some indicators may return None (insufficient warmup)."""
    result = calculate_indicators(sample_ohlcv_data)
    assert len(result) == 9
    # Even with short data, RSI(14) should have a value with 20 candles
    rsi = next(r for r in result if r.name == "RSI(14)")
    assert rsi.value is not None
