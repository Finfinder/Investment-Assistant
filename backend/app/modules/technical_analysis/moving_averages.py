import pandas as pd
import pandas_ta as ta

from app.core.models import MovingAverage, OHLCVData, SignalType

MA_PERIODS = (5, 10, 20, 50, 100, 200)


def calculate_moving_averages(ohlcv: list[OHLCVData]) -> list[MovingAverage]:
    """Calculate SMA and EMA for each period in MA_PERIODS.

    Signal: buy if latest close > MA value, sell if close < MA value.
    Returns one MovingAverage per period (6 items total).
    """
    if len(ohlcv) < 2:
        return []

    df = pd.DataFrame([item.model_dump() for item in ohlcv])
    close = df["close"]
    last_close = float(close.iloc[-1])

    results: list[MovingAverage] = []
    for period in MA_PERIODS:
        sma_series = ta.sma(close, length=period)
        ema_series = ta.ema(close, length=period)

        sma_val = _safe_last(sma_series)
        ema_val = _safe_last(ema_series)

        results.append(
            MovingAverage(
                period=period,
                sma_value=sma_val,
                sma_signal=_ma_signal(last_close, sma_val),
                ema_value=ema_val,
                ema_signal=_ma_signal(last_close, ema_val),
            )
        )
    return results


def _ma_signal(close: float, ma_value: float | None) -> SignalType:
    if ma_value is None:
        return SignalType.NEUTRAL
    if close > ma_value:
        return SignalType.BUY
    if close < ma_value:
        return SignalType.SELL
    return SignalType.NEUTRAL


def _safe_last(series: pd.Series | None) -> float | None:
    if series is None or series.empty:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)
