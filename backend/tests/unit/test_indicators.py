from app.core.models import IndicatorPreset, OHLCVData, SignalType
from app.modules.technical_analysis.indicators import _SIGNAL_KEYS, calculate_indicators
from app.modules.technical_analysis.presets import IndicatorParams, get_preset_params
from app.modules.technical_analysis.signal_rating import SIGNAL_RATING_CONFIG

# Default params match TradingView preset (all defaults)
DEFAULT_PARAMS = IndicatorParams()

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
    "ATR(14)",
    "BBP(13)",
    "STOCHRSI.K(14)",
    "ROC(15)",
]

EXPECTED_NAMES_INVESTING = [
    "RSI(14)",
    "STOCH.K(9)",
    "CCI(14)",
    "ADX(14)",
    "AO",
    "Momentum(10)",
    "MACD(12,26,9)",
    "Williams %R(14)",
    "UO(7,14,28)",
    "ATR(14)",
    "BBP(13)",
    "STOCHRSI.K(14)",
    "ROC(15)",
]


def test_returns_13_indicators(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    assert len(result) == 13


def test_indicator_names(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    names = [r.name for r in result]
    assert names == EXPECTED_NAMES


def test_indicator_names_investing_preset(sample_ohlcv_data_long):
    params = get_preset_params(IndicatorPreset.INVESTING)
    result = calculate_indicators(sample_ohlcv_data_long, params)
    names = [r.name for r in result]
    assert names == EXPECTED_NAMES_INVESTING


def test_indicators_with_tradingview_preset(sample_ohlcv_data_long):
    params = get_preset_params(IndicatorPreset.TRADINGVIEW)
    result = calculate_indicators(sample_ohlcv_data_long, params)
    names = [r.name for r in result]
    assert names == EXPECTED_NAMES


def test_all_have_values(sample_ohlcv_data_long):
    """With 250 candles, all indicators should produce non-None values."""
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    for ind in result:
        assert ind.value is not None, f"{ind.name} has None value"


def test_rsi_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    rsi = next(r for r in result if r.name == "RSI(14)")
    assert 0.0 <= rsi.value <= 100.0


def test_stochastic_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    stoch = next(r for r in result if r.name == "STOCH.K(14)")
    assert 0.0 <= stoch.value <= 100.0


def test_williams_r_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    willr = next(r for r in result if r.name == "Williams %R(14)")
    assert -100.0 <= willr.value <= 0.0


def test_uo_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    uo = next(r for r in result if r.name == "UO(7,14,28)")
    assert 0.0 <= uo.value <= 100.0


def test_signals_are_valid(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    valid = set(SignalType)
    for ind in result:
        assert ind.signal in valid, f"{ind.name} has invalid signal {ind.signal}"


def test_empty_input():
    assert calculate_indicators([], DEFAULT_PARAMS) == []


def test_single_candle():
    from datetime import UTC, datetime

    candle = OHLCVData(timestamp=datetime(2024, 1, 1, tzinfo=UTC), open=100, high=102, low=99, close=101, volume=1000)
    assert calculate_indicators([candle], DEFAULT_PARAMS) == []


def test_short_data_returns_none_values(sample_ohlcv_data):
    """With only 20 candles, some indicators may return None (insufficient warmup)."""
    result = calculate_indicators(sample_ohlcv_data, DEFAULT_PARAMS)
    assert len(result) == 13
    # Even with short data, RSI(14) should have a value with 20 candles
    rsi = next(r for r in result if r.name == "RSI(14)")
    assert rsi.value is not None


def test_atr_positive(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    atr = next(r for r in result if r.name == "ATR(14)")
    assert atr.value is not None
    assert atr.value >= 0.0
    assert atr.signal == SignalType.NEUTRAL


def test_signal_keys_cover_all_indicators_and_config(sample_ohlcv_data_long):
    """_SIGNAL_KEYS must map every produced indicator name and only valid config keys."""
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    produced_names = {r.name.split("(")[0] for r in result}
    # Every produced indicator name prefix has a mapping
    assert produced_names <= set(_SIGNAL_KEYS), f"Unmapped indicators: {produced_names - set(_SIGNAL_KEYS)}"
    # Every mapped key exists in SIGNAL_RATING_CONFIG
    assert set(_SIGNAL_KEYS.values()) <= set(SIGNAL_RATING_CONFIG), (
        f"Unknown keys: {set(_SIGNAL_KEYS.values()) - set(SIGNAL_RATING_CONFIG)}"
    )


def test_stochrsi_in_range(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    stochrsi = next(r for r in result if r.name == "STOCHRSI.K(14)")
    assert stochrsi.value is not None
    # Allow tiny floating-point overshoot (e.g. -5e-14)
    assert -1e-10 <= stochrsi.value <= 100.0 + 1e-10


def test_roc_has_value(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    roc = next(r for r in result if r.name == "ROC(15)")
    assert roc.value is not None


def test_bbp_has_value(sample_ohlcv_data_long):
    result = calculate_indicators(sample_ohlcv_data_long, DEFAULT_PARAMS)
    bbp = next(r for r in result if r.name == "BBP(13)")
    assert bbp.value is not None
