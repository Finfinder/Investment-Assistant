import pandas as pd
import pandas_ta as ta

from app.core.models import IndicatorValue, OHLCVData
from app.modules.technical_analysis._helpers import safe_last as _safe_last
from app.modules.technical_analysis.presets import IndicatorParams
from app.modules.technical_analysis.signal_rating import rate_signal

# Mapa prefiksu nazwy wskaźnika (IndicatorValue.name) na klucz konfiguracyjny rate_signal.
# Jedyne źródło prawdy wiążące typ sygnału z kluczem SIGNAL_RATING_CONFIG — używana w calculate_indicators.
_SIGNAL_KEYS: dict[str, str] = {
    "RSI": "rsi",
    "STOCH.K": "stochastic",
    "CCI": "cci",
    "ADX": "adx",
    "AO": "awesome_oscillator",
    "Momentum": "momentum",
    "MACD": "macd_crossover",
    "Williams %R": "williams_r",
    "UO": "ultimate_oscillator",
    "ATR": "atr",
    "BBP": "bull_bear_power",
    "STOCHRSI.K": "stochrsi",
    "ROC": "roc",
}


def calculate_indicators(ohlcv: list[OHLCVData], params: IndicatorParams) -> list[IndicatorValue]:
    """Calculate 9 oscillator / momentum indicators and assign signals.

    Parameters come from the selected preset (Investing / TradingView).
    """
    if len(ohlcv) < 2:
        return []

    df = pd.DataFrame([item.model_dump() for item in ohlcv])
    high, low, close = df["high"], df["low"], df["close"]

    results: list[IndicatorValue] = []

    # 1. RSI
    rsi_val = _safe_last(ta.rsi(close, length=params.rsi_length))
    results.append(
        IndicatorValue(
            name=f"RSI({params.rsi_length})", value=rsi_val, signal=rate_signal(_SIGNAL_KEYS["RSI"], rsi_val)
        )
    )

    # 2. Stochastic %K
    stoch_df = ta.stoch(high, low, close, k=params.stoch_k, d=params.stoch_d, smooth_k=params.stoch_smooth_k)
    stoch_k = _safe_last(stoch_df, col=0)
    results.append(
        IndicatorValue(
            name=f"STOCH.K({params.stoch_k})", value=stoch_k, signal=rate_signal(_SIGNAL_KEYS["STOCH.K"], stoch_k)
        )
    )

    # 3. CCI
    cci_val = _safe_last(ta.cci(high, low, close, length=params.cci_length))
    results.append(
        IndicatorValue(
            name=f"CCI({params.cci_length})", value=cci_val, signal=rate_signal(_SIGNAL_KEYS["CCI"], cci_val)
        )
    )

    # 4. ADX — signal depends on +DI / -DI direction
    adx_df = ta.adx(high, low, close, length=params.adx_length)
    adx_val = _safe_last(adx_df, col=0)
    plus_di = _safe_last(adx_df, col=1)
    minus_di = _safe_last(adx_df, col=2)
    results.append(
        IndicatorValue(
            name=f"ADX({params.adx_length})",
            value=adx_val,
            signal=rate_signal(_SIGNAL_KEYS["ADX"], adx_val, plus_di, minus_di),
        )
    )

    # 5. Awesome Oscillator
    ao_val = _safe_last(ta.ao(high, low, fast=params.ao_fast, slow=params.ao_slow))
    results.append(IndicatorValue(name="AO", value=ao_val, signal=rate_signal(_SIGNAL_KEYS["AO"], ao_val)))

    # 6. Momentum
    mom_val = _safe_last(ta.mom(close, length=params.momentum_length))
    results.append(
        IndicatorValue(
            name=f"Momentum({params.momentum_length})",
            value=mom_val,
            signal=rate_signal(_SIGNAL_KEYS["Momentum"], mom_val),
        )
    )

    # 7. MACD — value = MACD line, signal based on crossover (MACD vs Signal line)
    macd_df = ta.macd(close, fast=params.macd_fast, slow=params.macd_slow, signal=params.macd_signal)
    macd_line = _safe_last(macd_df, col=0)
    signal_line = _safe_last(macd_df, col=2)
    results.append(
        IndicatorValue(
            name=f"MACD({params.macd_fast},{params.macd_slow},{params.macd_signal})",
            value=macd_line,
            signal=rate_signal(_SIGNAL_KEYS["MACD"], macd_line, signal_line),
        )
    )

    # 8. Williams %R
    willr_val = _safe_last(ta.willr(high, low, close, length=params.willr_length))
    results.append(
        IndicatorValue(
            name=f"Williams %R({params.willr_length})",
            value=willr_val,
            signal=rate_signal(_SIGNAL_KEYS["Williams %R"], willr_val),
        )
    )

    # 9. Ultimate Oscillator
    uo_val = _safe_last(ta.uo(high, low, close, fast=params.uo_fast, medium=params.uo_medium, slow=params.uo_slow))
    results.append(
        IndicatorValue(
            name=f"UO({params.uo_fast},{params.uo_medium},{params.uo_slow})",
            value=uo_val,
            signal=rate_signal(_SIGNAL_KEYS["UO"], uo_val),
        )
    )

    # 10. ATR (volatility — always NEUTRAL signal)
    atr_val = _safe_last(ta.atr(high, low, close, length=params.atr_length))
    results.append(
        IndicatorValue(
            name=f"ATR({params.atr_length})", value=atr_val, signal=rate_signal(_SIGNAL_KEYS["ATR"], atr_val)
        )
    )

    # 11. Bull Bear Power — bull = high - EMA, bear = low - EMA, bbp = bull + bear
    ema_for_bbp = ta.ema(close, length=params.bbp_length)
    last_ema = _safe_last(pd.DataFrame({"v": ema_for_bbp}), col=0) if ema_for_bbp is not None else None
    last_high = _safe_last(pd.DataFrame({"v": high}), col=0)
    last_low = _safe_last(pd.DataFrame({"v": low}), col=0)
    if last_ema is not None and last_high is not None and last_low is not None:
        bbp_val = (last_high - last_ema) + (last_low - last_ema)
    else:
        bbp_val = None
    results.append(
        IndicatorValue(
            name=f"BBP({params.bbp_length})", value=bbp_val, signal=rate_signal(_SIGNAL_KEYS["BBP"], bbp_val)
        )
    )

    # 12. Stochastic RSI
    stochrsi_df = ta.stochrsi(
        close,
        length=params.stochrsi_length,
        rsi_length=params.stochrsi_rsi_length,
        k=params.stochrsi_k,
        d=params.stochrsi_d,
    )
    stochrsi_k = _safe_last(stochrsi_df, col=0)
    results.append(
        IndicatorValue(
            name=f"STOCHRSI.K({params.stochrsi_length})",
            value=stochrsi_k,
            signal=rate_signal(_SIGNAL_KEYS["STOCHRSI.K"], stochrsi_k),
        )
    )

    # 13. Rate of Change
    roc_val = _safe_last(ta.roc(close, length=params.roc_length))
    results.append(
        IndicatorValue(
            name=f"ROC({params.roc_length})", value=roc_val, signal=rate_signal(_SIGNAL_KEYS["ROC"], roc_val)
        )
    )

    return results
