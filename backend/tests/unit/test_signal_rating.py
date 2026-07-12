import pytest

from app.core.models import SignalType
from app.modules.technical_analysis.signal_rating import (
    rate_adx,
    rate_atr,
    rate_awesome_oscillator,
    rate_bull_bear_power,
    rate_cci,
    rate_macd_crossover,
    rate_macd_histogram,
    rate_momentum,
    rate_roc,
    rate_rsi,
    rate_signal,
    rate_stochastic,
    rate_stochrsi,
    rate_ultimate_oscillator,
    rate_williams_r,
)

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


# --- RSI ---


def test_rate_rsi_strong_buy():

    assert rate_rsi(15.0) == SignalType.STRONG_BUY


def test_rate_rsi_buy():

    assert rate_rsi(25.0) == SignalType.BUY


def test_rate_rsi_neutral():

    assert rate_rsi(50.0) == SignalType.NEUTRAL


def test_rate_rsi_sell():

    assert rate_rsi(75.0) == SignalType.SELL


def test_rate_rsi_strong_sell():

    assert rate_rsi(85.0) == SignalType.STRONG_SELL


def test_rate_rsi_none():

    assert rate_rsi(None) == SignalType.NEUTRAL


# --- Stochastic ---


def test_rate_stochastic_buy():

    assert rate_stochastic(10.0) == SignalType.BUY


def test_rate_stochastic_sell():

    assert rate_stochastic(90.0) == SignalType.SELL


def test_rate_stochastic_neutral():

    assert rate_stochastic(50.0) == SignalType.NEUTRAL


# --- CCI ---


def test_rate_cci_strong_buy():

    assert rate_cci(-250.0) == SignalType.STRONG_BUY


def test_rate_cci_buy():

    assert rate_cci(-150.0) == SignalType.BUY


def test_rate_cci_sell():

    assert rate_cci(150.0) == SignalType.SELL


def test_rate_cci_strong_sell():

    assert rate_cci(250.0) == SignalType.STRONG_SELL


# --- ADX ---


def test_rate_adx_no_trend():

    assert rate_adx(15.0, 30.0, 20.0) == SignalType.NEUTRAL


def test_rate_adx_buy():

    assert rate_adx(25.0, 30.0, 20.0) == SignalType.BUY


def test_rate_adx_strong_buy():

    assert rate_adx(45.0, 30.0, 20.0) == SignalType.STRONG_BUY


def test_rate_adx_sell():

    assert rate_adx(25.0, 10.0, 30.0) == SignalType.SELL


def test_rate_adx_strong_sell():

    assert rate_adx(45.0, 10.0, 30.0) == SignalType.STRONG_SELL


def test_rate_adx_none():

    assert rate_adx(None, None, None) == SignalType.NEUTRAL


# --- MACD histogram ---


def test_rate_macd_histogram_strong_buy():

    assert rate_macd_histogram(0.5, 0.2) == SignalType.STRONG_BUY


def test_rate_macd_histogram_buy():

    assert rate_macd_histogram(0.5) == SignalType.BUY


def test_rate_macd_histogram_strong_sell():

    assert rate_macd_histogram(-0.5, -0.2) == SignalType.STRONG_SELL


def test_rate_macd_histogram_sell():

    assert rate_macd_histogram(-0.5) == SignalType.SELL


def test_rate_macd_histogram_neutral():

    assert rate_macd_histogram(0.0) == SignalType.NEUTRAL


# --- Awesome Oscillator ---


def test_rate_ao_buy():

    assert rate_awesome_oscillator(5.0) == SignalType.BUY


def test_rate_ao_sell():

    assert rate_awesome_oscillator(-5.0) == SignalType.SELL


# --- Momentum ---


def test_rate_momentum_buy():

    assert rate_momentum(3.0) == SignalType.BUY


def test_rate_momentum_sell():

    assert rate_momentum(-3.0) == SignalType.SELL


# --- Williams %R ---


def test_rate_williams_r_buy():

    assert rate_williams_r(-90.0) == SignalType.BUY


def test_rate_williams_r_sell():

    assert rate_williams_r(-10.0) == SignalType.SELL


def test_rate_williams_r_neutral():

    assert rate_williams_r(-50.0) == SignalType.NEUTRAL


# --- Ultimate Oscillator ---


def test_rate_uo_buy():

    assert rate_ultimate_oscillator(25.0) == SignalType.BUY


def test_rate_uo_sell():

    assert rate_ultimate_oscillator(75.0) == SignalType.SELL


def test_rate_uo_neutral():

    assert rate_ultimate_oscillator(50.0) == SignalType.NEUTRAL


def test_rate_uo_none():

    assert rate_ultimate_oscillator(None) == SignalType.NEUTRAL


# --- MACD crossover ---


def test_rate_macd_crossover_buy():

    assert rate_macd_crossover(1.5, 0.5) == SignalType.BUY


def test_rate_macd_crossover_sell():

    assert rate_macd_crossover(-0.5, 0.5) == SignalType.SELL


def test_rate_macd_crossover_neutral_none():

    assert rate_macd_crossover(None, None) == SignalType.NEUTRAL


def test_rate_macd_crossover_neutral_equal():

    assert rate_macd_crossover(1.0, 1.0) == SignalType.NEUTRAL


def test_rate_macd_crossover_macd_none():

    assert rate_macd_crossover(None, 0.5) == SignalType.NEUTRAL


def test_rate_macd_crossover_signal_none():

    assert rate_macd_crossover(0.5, None) == SignalType.NEUTRAL


# --- ATR ---


def test_rate_atr_always_neutral():

    assert rate_atr(2.5) == SignalType.NEUTRAL


def test_rate_atr_none():

    assert rate_atr(None) == SignalType.NEUTRAL


# --- Bull Bear Power ---


def test_rate_bbp_buy():

    assert rate_bull_bear_power(1.5) == SignalType.BUY


def test_rate_bbp_sell():

    assert rate_bull_bear_power(-1.5) == SignalType.SELL


def test_rate_bbp_neutral():

    assert rate_bull_bear_power(0.0) == SignalType.NEUTRAL


def test_rate_bbp_none():

    assert rate_bull_bear_power(None) == SignalType.NEUTRAL


# --- Stochastic RSI ---


def test_rate_stochrsi_buy():

    assert rate_stochrsi(10.0) == SignalType.BUY


def test_rate_stochrsi_sell():

    assert rate_stochrsi(90.0) == SignalType.SELL


def test_rate_stochrsi_neutral():

    assert rate_stochrsi(50.0) == SignalType.NEUTRAL


def test_rate_stochrsi_none():

    assert rate_stochrsi(None) == SignalType.NEUTRAL


# --- ROC ---


def test_rate_roc_buy():

    assert rate_roc(2.0) == SignalType.BUY


def test_rate_roc_sell():

    assert rate_roc(-2.0) == SignalType.SELL


def test_rate_roc_neutral():

    assert rate_roc(0.0) == SignalType.NEUTRAL


def test_rate_roc_none():

    assert rate_roc(None) == SignalType.NEUTRAL
