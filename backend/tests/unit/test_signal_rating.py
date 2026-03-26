from app.core.models import SignalType
from app.modules.technical_analysis.signal_rating import (
    rate_adx,
    rate_awesome_oscillator,
    rate_cci,
    rate_macd_histogram,
    rate_momentum,
    rate_rsi,
    rate_stochastic,
    rate_ultimate_oscillator,
    rate_williams_r,
)

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
