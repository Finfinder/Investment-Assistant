from app.core.models import SignalType


def rate_rsi(value: float | None) -> SignalType:
    """RSI thresholds: <20 strong_buy, 20-30 buy, 70-80 sell, >80 strong_sell."""
    if value is None:
        return SignalType.NEUTRAL
    if value < 20:
        return SignalType.STRONG_BUY
    if value < 30:
        return SignalType.BUY
    if value > 80:
        return SignalType.STRONG_SELL
    if value > 70:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_stochastic(k_value: float | None) -> SignalType:
    """Stochastic %K: <20 buy (oversold), >80 sell (overbought)."""
    if k_value is None:
        return SignalType.NEUTRAL
    if k_value < 20:
        return SignalType.BUY
    if k_value > 80:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_cci(value: float | None) -> SignalType:
    """CCI: <-200 strong_buy, <-100 buy, >100 sell, >200 strong_sell."""
    if value is None:
        return SignalType.NEUTRAL
    if value < -200:
        return SignalType.STRONG_BUY
    if value < -100:
        return SignalType.BUY
    if value > 200:
        return SignalType.STRONG_SELL
    if value > 100:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_adx(adx_value: float | None, plus_di: float | None = None, minus_di: float | None = None) -> SignalType:
    """ADX: <20 neutral (no trend), >20 direction from +DI vs -DI, >40 strong signal."""
    if adx_value is None or plus_di is None or minus_di is None:
        return SignalType.NEUTRAL
    if adx_value < 20:
        return SignalType.NEUTRAL
    if plus_di > minus_di:
        return SignalType.STRONG_BUY if adx_value >= 40 else SignalType.BUY
    if minus_di > plus_di:
        return SignalType.STRONG_SELL if adx_value >= 40 else SignalType.SELL
    return SignalType.NEUTRAL


def rate_awesome_oscillator(value: float | None) -> SignalType:
    """AO: >0 buy, <0 sell."""
    if value is None:
        return SignalType.NEUTRAL
    if value > 0:
        return SignalType.BUY
    if value < 0:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_momentum(value: float | None) -> SignalType:
    """Momentum: >0 buy, <0 sell."""
    if value is None:
        return SignalType.NEUTRAL
    if value > 0:
        return SignalType.BUY
    if value < 0:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_macd_histogram(hist_value: float | None, prev_hist: float | None = None) -> SignalType:
    """MACD histogram: >0 & rising strong_buy, >0 buy, <0 & falling strong_sell, <0 sell."""
    if hist_value is None:
        return SignalType.NEUTRAL
    if hist_value > 0:
        if prev_hist is not None and hist_value > prev_hist:
            return SignalType.STRONG_BUY
        return SignalType.BUY
    if hist_value < 0:
        if prev_hist is not None and hist_value < prev_hist:
            return SignalType.STRONG_SELL
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_williams_r(value: float | None) -> SignalType:
    """Williams %R: <-80 buy (oversold), >-20 sell (overbought)."""
    if value is None:
        return SignalType.NEUTRAL
    if value < -80:
        return SignalType.BUY
    if value > -20:
        return SignalType.SELL
    return SignalType.NEUTRAL


def rate_ultimate_oscillator(value: float | None) -> SignalType:
    """Ultimate Oscillator: <30 buy, >70 sell."""
    if value is None:
        return SignalType.NEUTRAL
    if value < 30:
        return SignalType.BUY
    if value > 70:
        return SignalType.SELL
    return SignalType.NEUTRAL
