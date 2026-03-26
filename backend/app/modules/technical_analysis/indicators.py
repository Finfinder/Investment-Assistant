import pandas as pd
import pandas_ta as ta

from app.core.models import IndicatorValue, OHLCVData
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


def _safe_last(data: pd.Series | pd.DataFrame | None, col: int = 0) -> float | None:
    """Extract the last value from a Series or the given column of a DataFrame."""
    if data is None:
        return None
    series = data.iloc[:, col] if isinstance(data, pd.DataFrame) else data
    if series.empty:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)


def calculate_indicators(ohlcv: list[OHLCVData]) -> list[IndicatorValue]:
    """Calculate 9 oscillator / momentum indicators and assign signals.

    Returns one IndicatorValue per indicator:
    RSI(14), STOCH.K(14), CCI(20), ADX(14), AO, Momentum(10),
    MACD(12,26,9), Williams %R(14), UO(7,14,28).
    """
    if len(ohlcv) < 2:
        return []

    df = pd.DataFrame([item.model_dump() for item in ohlcv])
    high, low, close = df["high"], df["low"], df["close"]

    results: list[IndicatorValue] = []

    # 1. RSI(14)
    rsi_val = _safe_last(ta.rsi(close, length=14))
    results.append(IndicatorValue(name="RSI(14)", value=rsi_val, signal=rate_rsi(rsi_val)))

    # 2. Stochastic %K(14,3,3)
    stoch_df = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
    stoch_k = _safe_last(stoch_df, col=0)
    results.append(IndicatorValue(name="STOCH.K(14)", value=stoch_k, signal=rate_stochastic(stoch_k)))

    # 3. CCI(20)
    cci_val = _safe_last(ta.cci(high, low, close, length=20))
    results.append(IndicatorValue(name="CCI(20)", value=cci_val, signal=rate_cci(cci_val)))

    # 4. ADX(14) — signal depends on +DI / -DI direction
    adx_df = ta.adx(high, low, close, length=14)
    adx_val = _safe_last(adx_df, col=0)
    plus_di = _safe_last(adx_df, col=1)
    minus_di = _safe_last(adx_df, col=2)
    results.append(IndicatorValue(name="ADX(14)", value=adx_val, signal=rate_adx(adx_val, plus_di, minus_di)))

    # 5. Awesome Oscillator (5, 34)
    ao_val = _safe_last(ta.ao(high, low, fast=5, slow=34))
    results.append(IndicatorValue(name="AO", value=ao_val, signal=rate_awesome_oscillator(ao_val)))

    # 6. Momentum(10)
    mom_val = _safe_last(ta.mom(close, length=10))
    results.append(IndicatorValue(name="Momentum(10)", value=mom_val, signal=rate_momentum(mom_val)))

    # 7. MACD(12,26,9) — value = MACD line, signal based on histogram
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_line = _safe_last(macd_df, col=0)
    macd_hist = _safe_last(macd_df, col=1)
    prev_hist = None
    if macd_df is not None and len(macd_df) >= 2:
        prev = macd_df.iloc[-2, 1]
        prev_hist = None if pd.isna(prev) else float(prev)
    results.append(
        IndicatorValue(name="MACD(12,26,9)", value=macd_line, signal=rate_macd_histogram(macd_hist, prev_hist))
    )

    # 8. Williams %R(14)
    willr_val = _safe_last(ta.willr(high, low, close, length=14))
    results.append(IndicatorValue(name="Williams %R(14)", value=willr_val, signal=rate_williams_r(willr_val)))

    # 9. Ultimate Oscillator(7,14,28)
    uo_val = _safe_last(ta.uo(high, low, close, fast=7, medium=14, slow=28))
    results.append(IndicatorValue(name="UO(7,14,28)", value=uo_val, signal=rate_ultimate_oscillator(uo_val)))

    return results
