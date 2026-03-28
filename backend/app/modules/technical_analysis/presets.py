"""Indicator parameter presets for different platform configurations."""

from dataclasses import dataclass

from app.core.models import IndicatorPreset


@dataclass(frozen=True)
class IndicatorParams:
    """Frozen parameter set for all technical indicators."""

    # RSI
    rsi_length: int = 14
    # Stochastic
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_smooth_k: int = 3
    # CCI
    cci_length: int = 20
    # ADX
    adx_length: int = 14
    # Awesome Oscillator
    ao_fast: int = 5
    ao_slow: int = 34
    # Momentum
    momentum_length: int = 10
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # Williams %R
    willr_length: int = 14
    # Ultimate Oscillator
    uo_fast: int = 7
    uo_medium: int = 14
    uo_slow: int = 28
    # ATR
    atr_length: int = 14
    # Bull/Bear Power
    bbp_length: int = 13
    # Stochastic RSI
    stochrsi_length: int = 14
    stochrsi_rsi_length: int = 14
    stochrsi_k: int = 3
    stochrsi_d: int = 3
    # ROC
    roc_length: int = 15


PRESETS: dict[IndicatorPreset, IndicatorParams] = {
    IndicatorPreset.INVESTING: IndicatorParams(
        stoch_k=9,
        stoch_d=6,
        stoch_smooth_k=1,
        cci_length=14,
        bbp_length=13,
        stochrsi_length=14,
        stochrsi_rsi_length=14,
        stochrsi_k=14,
        stochrsi_d=14,
        roc_length=15,
    ),
    IndicatorPreset.TRADINGVIEW: IndicatorParams(),
}


def get_preset_params(preset: IndicatorPreset) -> IndicatorParams:
    """Return indicator parameters for the given preset."""
    params = PRESETS.get(preset)
    if params is None:
        raise ValueError(f"Unknown preset: {preset}")
    return params
