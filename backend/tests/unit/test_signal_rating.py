import pytest

from app.core.models import SignalType
from app.modules.technical_analysis.signal_rating import rate_signal

# Przypadki testowe przez skonsolidowaną ścieżkę rate_signal:

# (signal_type, args, oczekiwany SignalType)

RATE_SIGNAL_CASES = [
    ("rsi", (15.0,), SignalType.STRONG_BUY),
    ("rsi", (25.0,), SignalType.BUY),
    ("rsi", (50.0,), SignalType.NEUTRAL),
    ("rsi", (75.0,), SignalType.SELL),
    ("rsi", (85.0,), SignalType.STRONG_SELL),
    ("rsi", (None,), SignalType.NEUTRAL),
    ("stochastic", (10.0,), SignalType.BUY),
    ("stochastic", (90.0,), SignalType.SELL),
    ("stochastic", (50.0,), SignalType.NEUTRAL),
    ("stochastic", (None,), SignalType.NEUTRAL),
    ("cci", (-250.0,), SignalType.STRONG_BUY),
    ("cci", (-150.0,), SignalType.BUY),
    ("cci", (150.0,), SignalType.SELL),
    ("cci", (250.0,), SignalType.STRONG_SELL),
    ("cci", (None,), SignalType.NEUTRAL),
    ("adx", (15.0, 30.0, 20.0), SignalType.NEUTRAL),
    ("adx", (25.0, 30.0, 20.0), SignalType.BUY),
    ("adx", (45.0, 30.0, 20.0), SignalType.STRONG_BUY),
    ("adx", (25.0, 10.0, 30.0), SignalType.SELL),
    ("adx", (45.0, 10.0, 30.0), SignalType.STRONG_SELL),
    ("adx", (None, None, None), SignalType.NEUTRAL),
    ("awesome_oscillator", (5.0,), SignalType.BUY),
    ("awesome_oscillator", (-5.0,), SignalType.SELL),
    ("awesome_oscillator", (0.0,), SignalType.NEUTRAL),
    ("awesome_oscillator", (None,), SignalType.NEUTRAL),
    ("momentum", (3.0,), SignalType.BUY),
    ("momentum", (-3.0,), SignalType.SELL),
    ("momentum", (0.0,), SignalType.NEUTRAL),
    ("momentum", (None,), SignalType.NEUTRAL),
    ("macd_histogram", (0.5, 0.2), SignalType.STRONG_BUY),
    ("macd_histogram", (0.5,), SignalType.BUY),
    ("macd_histogram", (-0.5, -0.2), SignalType.STRONG_SELL),
    ("macd_histogram", (-0.5,), SignalType.SELL),
    ("macd_histogram", (0.0,), SignalType.NEUTRAL),
    ("macd_histogram", (None,), SignalType.NEUTRAL),
    ("williams_r", (-90.0,), SignalType.BUY),
    ("williams_r", (-10.0,), SignalType.SELL),
    ("williams_r", (-50.0,), SignalType.NEUTRAL),
    ("williams_r", (None,), SignalType.NEUTRAL),
    ("ultimate_oscillator", (25.0,), SignalType.BUY),
    ("ultimate_oscillator", (75.0,), SignalType.SELL),
    ("ultimate_oscillator", (50.0,), SignalType.NEUTRAL),
    ("ultimate_oscillator", (None,), SignalType.NEUTRAL),
    ("macd_crossover", (1.5, 0.5), SignalType.BUY),
    ("macd_crossover", (-0.5, 0.5), SignalType.SELL),
    ("macd_crossover", (None, None), SignalType.NEUTRAL),
    ("macd_crossover", (1.0, 1.0), SignalType.NEUTRAL),
    ("macd_crossover", (None, 0.5), SignalType.NEUTRAL),
    ("macd_crossover", (0.5, None), SignalType.NEUTRAL),
    ("atr", (2.5,), SignalType.NEUTRAL),
    ("atr", (None,), SignalType.NEUTRAL),
    ("bull_bear_power", (1.5,), SignalType.BUY),
    ("bull_bear_power", (-1.5,), SignalType.SELL),
    ("bull_bear_power", (0.0,), SignalType.NEUTRAL),
    ("bull_bear_power", (None,), SignalType.NEUTRAL),
    ("stochrsi", (10.0,), SignalType.BUY),
    ("stochrsi", (90.0,), SignalType.SELL),
    ("stochrsi", (50.0,), SignalType.NEUTRAL),
    ("stochrsi", (None,), SignalType.NEUTRAL),
    ("roc", (2.0,), SignalType.BUY),
    ("roc", (-2.0,), SignalType.SELL),
    ("roc", (0.0,), SignalType.NEUTRAL),
    ("roc", (None,), SignalType.NEUTRAL),
]


@pytest.mark.parametrize(("signal_type", "args", "expected"), RATE_SIGNAL_CASES)
def test_rate_signal_consolidated(signal_type, args, expected):

    assert rate_signal(signal_type, *args) == expected


def test_rate_signal_unknown_type_raises_value_error():
    with pytest.raises(ValueError, match="Unknown signal_type"):
        rate_signal("does_not_exist", 1.0)


def test_rate_signal_bands_rejects_extra_values():
    with pytest.raises(TypeError, match="expects 1 value"):
        rate_signal("rsi", 15.0, 30.0)
