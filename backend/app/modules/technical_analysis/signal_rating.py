from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel

from app.core.models import SignalType


class BandOp(StrEnum):
    LT = "lt"  # pragma: no mutate
    GT = "gt"  # pragma: no mutate


class BandRule(BaseModel):
    op: BandOp
    threshold: float
    signal: SignalType


class SignalRatingConfig(BaseModel):
    kind: str
    bands: list[BandRule] = []


def _rate_bands(value: float | None, config: SignalRatingConfig) -> SignalType:
    if value is None:
        return SignalType.NEUTRAL
    for rule in config.bands:
        if rule.op == BandOp.LT and value < rule.threshold:
            return rule.signal
        if rule.op == BandOp.GT and value > rule.threshold:
            return rule.signal
    return SignalType.NEUTRAL


def _rate_crossover(macd_line: float | None, signal_line: float | None) -> SignalType:
    if macd_line is None or signal_line is None:
        return SignalType.NEUTRAL
    if macd_line > signal_line:
        return SignalType.BUY
    if macd_line < signal_line:
        return SignalType.SELL
    return SignalType.NEUTRAL


def _rate_directional(adx_value: float | None, plus_di: float | None, minus_di: float | None) -> SignalType:
    if adx_value is None or plus_di is None or minus_di is None:
        return SignalType.NEUTRAL
    if adx_value < 20:
        return SignalType.NEUTRAL
    if plus_di > minus_di:
        return SignalType.STRONG_BUY if adx_value >= 40 else SignalType.BUY
    if minus_di > plus_di:
        return SignalType.STRONG_SELL if adx_value >= 40 else SignalType.SELL
    return SignalType.NEUTRAL


def _rate_histogram(hist_value: float | None, prev_hist: float | None = None) -> SignalType:
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


def _rate_neutral(*values: float | None) -> SignalType:
    return SignalType.NEUTRAL


_RATERS: dict[str, Callable[..., SignalType]] = {
    "crossover": _rate_crossover,
    "directional": _rate_directional,
    "histogram": _rate_histogram,
    "neutral": _rate_neutral,
}

SIGNAL_RATING_CONFIG: dict[str, SignalRatingConfig] = {
    "rsi": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=20, signal=SignalType.STRONG_BUY),
            BandRule(op=BandOp.LT, threshold=30, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=80, signal=SignalType.STRONG_SELL),
            BandRule(op=BandOp.GT, threshold=70, signal=SignalType.SELL),
        ],
    ),
    "stochastic": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=20, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=80, signal=SignalType.SELL),
        ],
    ),
    "cci": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=-200, signal=SignalType.STRONG_BUY),
            BandRule(op=BandOp.LT, threshold=-100, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=200, signal=SignalType.STRONG_SELL),
            BandRule(op=BandOp.GT, threshold=100, signal=SignalType.SELL),
        ],
    ),
    "adx": SignalRatingConfig(kind="directional"),
    "awesome_oscillator": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.GT, threshold=0, signal=SignalType.BUY),
            BandRule(op=BandOp.LT, threshold=0, signal=SignalType.SELL),
        ],
    ),
    "momentum": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.GT, threshold=0, signal=SignalType.BUY),
            BandRule(op=BandOp.LT, threshold=0, signal=SignalType.SELL),
        ],
    ),
    "macd_histogram": SignalRatingConfig(kind="histogram"),
    "williams_r": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=-80, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=-20, signal=SignalType.SELL),
        ],
    ),
    "ultimate_oscillator": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=30, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=70, signal=SignalType.SELL),
        ],
    ),
    "macd_crossover": SignalRatingConfig(kind="crossover"),
    "atr": SignalRatingConfig(kind="neutral"),
    "bull_bear_power": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.GT, threshold=0, signal=SignalType.BUY),
            BandRule(op=BandOp.LT, threshold=0, signal=SignalType.SELL),
        ],
    ),
    "stochrsi": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.LT, threshold=20, signal=SignalType.BUY),
            BandRule(op=BandOp.GT, threshold=80, signal=SignalType.SELL),
        ],
    ),
    "roc": SignalRatingConfig(
        kind="bands",
        bands=[
            BandRule(op=BandOp.GT, threshold=0, signal=SignalType.BUY),
            BandRule(op=BandOp.LT, threshold=0, signal=SignalType.SELL),
        ],
    ),
}


def rate_signal(signal_type: str, *values: float | None) -> SignalType:
    """Oceń sygnał przez skonsolidowaną, sterowaną konfiguracją logikę.

    Wybiera strategię na podstawie `SIGNAL_RATING_CONFIG[signal_type].kind`.
    """
    if signal_type not in SIGNAL_RATING_CONFIG:
        valid = ", ".join(sorted(SIGNAL_RATING_CONFIG))  # pragma: no mutate
        raise ValueError(f"Unknown signal_type '{signal_type}'. Valid types: {valid}")  # pragma: no mutate
    config = SIGNAL_RATING_CONFIG[signal_type]
    if config.kind != "bands" and config.kind not in _RATERS:
        raise ValueError(f"Unknown rating kind '{config.kind}' for signal_type '{signal_type}'")  # pragma: no mutate
    if config.kind == "bands":
        if len(values) > 1:
            msg = f"Signal type '{signal_type}' (kind=bands) expects 1 value, got {len(values)}"
            raise TypeError(msg)  # pragma: no mutate
        return _rate_bands(values[0] if values else None, config)
    return _RATERS[config.kind](*values)


def rate_rsi(value: float | None) -> SignalType:
    """RSI thresholds: <20 strong_buy, 20-30 buy, 70-80 sell, >80 strong_sell."""
    return rate_signal("rsi", value)


def rate_stochastic(k_value: float | None) -> SignalType:
    """Stochastic %K: <20 buy (oversold), >80 sell (overbought)."""
    return rate_signal("stochastic", k_value)


def rate_cci(value: float | None) -> SignalType:
    """CCI: <-200 strong_buy, <-100 buy, >100 sell, >200 strong_sell."""
    return rate_signal("cci", value)


def rate_adx(adx_value: float | None, plus_di: float | None = None, minus_di: float | None = None) -> SignalType:
    """ADX: <20 neutral (no trend), >20 direction from +DI vs -DI, >40 strong signal."""
    return rate_signal("adx", adx_value, plus_di, minus_di)


def rate_awesome_oscillator(value: float | None) -> SignalType:
    """AO: >0 buy, <0 sell."""
    return rate_signal("awesome_oscillator", value)


def rate_momentum(value: float | None) -> SignalType:
    """Momentum: >0 buy, <0 sell."""
    return rate_signal("momentum", value)


def rate_macd_histogram(hist_value: float | None, prev_hist: float | None = None) -> SignalType:
    """MACD histogram: >0 & rising strong_buy, >0 buy, <0 & falling strong_sell, <0 sell."""
    return rate_signal("macd_histogram", hist_value, prev_hist)


def rate_williams_r(value: float | None) -> SignalType:
    """Williams %R: <-80 buy (oversold), >-20 sell (overbought)."""
    return rate_signal("williams_r", value)


def rate_ultimate_oscillator(value: float | None) -> SignalType:
    """Ultimate Oscillator: <30 buy, >70 sell."""
    return rate_signal("ultimate_oscillator", value)


def rate_macd_crossover(macd_line: float | None, signal_line: float | None) -> SignalType:
    """MACD crossover: MACD > Signal = buy, MACD < Signal = sell."""
    return rate_signal("macd_crossover", macd_line, signal_line)


def rate_atr(value: float | None) -> SignalType:
    """ATR is a volatility measure — always NEUTRAL (informational only)."""
    return rate_signal("atr", value)


def rate_bull_bear_power(value: float | None) -> SignalType:
    """Bull Bear Power: >0 buy (bulls dominate), <0 sell (bears dominate)."""
    return rate_signal("bull_bear_power", value)


def rate_stochrsi(value: float | None) -> SignalType:
    """Stochastic RSI %K: <20 buy (oversold), >80 sell (overbought)."""
    return rate_signal("stochrsi", value)


def rate_roc(value: float | None) -> SignalType:
    """Rate of Change: >0 buy, <0 sell."""
    return rate_signal("roc", value)
