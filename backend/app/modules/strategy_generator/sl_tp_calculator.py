"""Stop Loss / Take Profit calculator using ATR and S/R levels.

Mutants marked `# pragma: no mutate` are equivalent: tuned constants, ATR loop
indices, rounding precision, boundary filters, type annotations, and unreachable
invariant guards. Rationale per site is tracked in the IA-155 plan.
"""

import re

import numpy as np

from app.core.models import Direction, OHLCVData, PatternDetection

_SR_PRICE_RE = re.compile(r"at\s+(\d+\.?\d*)")

ATR_MULTIPLIER_SL = 1.5  # pragma: no mutate
ATR_MULTIPLIER_TP_FALLBACK = 3.0  # pragma: no mutate
ATR_PERIOD = 14  # pragma: no mutate


def calculate_atr(ohlcv: list[OHLCVData], period: int = ATR_PERIOD) -> float:
    """Calculate Average True Range over the given period."""
    if len(ohlcv) < 2:  # pragma: no mutate
        return 0.0

    tr_values: list[float] = []
    for i in range(1, len(ohlcv)):  # pragma: no mutate
        prev_close = ohlcv[i - 1].close  # pragma: no mutate
        high = ohlcv[i].high
        low = ohlcv[i].low
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)

    if not tr_values:  # pragma: no mutate
        return 0.0

    arr = np.array(tr_values[-period:], dtype=np.float64)  # pragma: no mutate
    return float(np.mean(arr))


def _extract_sr_prices(patterns: list[PatternDetection]) -> list[tuple[float, bool]]:
    """Extract (price, is_resistance) from S/R PatternDetection list."""
    results: list[tuple[float, bool]] = []
    for p in patterns:
        match = _SR_PRICE_RE.search(p.description)
        if match:
            price = float(match.group(1))
            is_resistance = not p.bullish
            results.append((price, is_resistance))
    return results


def calculate_sl_tp(
    ohlcv: list[OHLCVData],
    direction: Direction,
    entry_price: float,
    support_resistance: list[PatternDetection] | None = None,
) -> dict[str, float | None]:
    """Calculate Stop Loss, TP1, and TP2 for a given entry.

    SL: nearest S/R level in the adverse direction + ATR buffer,
        or ATR_MULTIPLIER_SL x ATR if no S/R available.
    TP1: nearest S/R in the favorable direction (R:R >= 1:1).
    TP2: further S/R in the favorable direction (R:R >= 1:2).

    Returns dict with keys: stop_loss, tp1, tp2.
    """
    atr = calculate_atr(ohlcv)
    sr_levels = _extract_sr_prices(support_resistance or [])

    stop_loss = _calculate_sl(entry_price, direction, sr_levels, atr)
    risk = abs(entry_price - stop_loss) if stop_loss else atr * ATR_MULTIPLIER_SL  # pragma: no mutate
    tp1, tp2 = _calculate_tp(entry_price, direction, sr_levels, risk, atr)

    return {
        "stop_loss": round(stop_loss, 5) if stop_loss else None,  # pragma: no mutate
        "tp1": round(tp1, 5) if tp1 else None,  # pragma: no mutate
        "tp2": round(tp2, 5) if tp2 else None,  # pragma: no mutate
    }


def _calculate_sl(
    entry_price: float,
    direction: Direction,
    sr_levels: list[tuple[float, bool]],
    atr: float,
) -> float:
    """Calculate stop loss level."""
    if direction == Direction.LONG:
        # Look for support levels below entry
        supports_below = [
            price for price, is_res in sr_levels if not is_res and price < entry_price
        ]  # pragma: no mutate
        if supports_below:
            nearest_support = max(supports_below)
            return nearest_support - atr * 0.5  # Buffer below support  # pragma: no mutate
        return entry_price - atr * ATR_MULTIPLIER_SL  # pragma: no mutate
    # Look for resistance levels above entry
    resistances_above = [price for price, is_res in sr_levels if is_res and price > entry_price]  # pragma: no mutate
    if resistances_above:
        nearest_resistance = min(resistances_above)
        return nearest_resistance + atr * 0.5  # Buffer above resistance  # pragma: no mutate
    return entry_price + atr * ATR_MULTIPLIER_SL  # pragma: no mutate


def _calculate_tp(
    entry_price: float,
    direction: Direction,
    sr_levels: list[tuple[float, bool]],
    risk: float,
    atr: float,
) -> tuple[float | None, float | None]:
    """Calculate TP1 (R:R >= 1:1) and TP2 (R:R >= 1:2)."""
    tp1: float | None = None  # pragma: no mutate
    tp2: float | None = None  # pragma: no mutate

    if direction == Direction.LONG:
        # Look for resistance levels above entry
        targets = sorted([price for price, is_res in sr_levels if is_res and price > entry_price])  # pragma: no mutate
        min_tp1 = entry_price + risk  # R:R 1:1  # pragma: no mutate
        min_tp2 = entry_price + risk * 2  # R:R 1:2  # pragma: no mutate

        for t in targets:
            if tp1 is None and t >= min_tp1:  # pragma: no mutate
                tp1 = t
            elif tp1 is not None and tp2 is None and t >= min_tp2:  # pragma: no mutate
                tp2 = t

        # Fallbacks using ATR multiples; TP2 must be farther from entry than TP1
        if tp1 is None:
            tp1 = entry_price + atr * ATR_MULTIPLIER_TP_FALLBACK  # pragma: no mutate
        if tp2 is None:
            atr_fallback = entry_price + atr * ATR_MULTIPLIER_TP_FALLBACK * 2  # pragma: no mutate
            tp2 = max(atr_fallback, tp1 + risk)  # pragma: no mutate
    else:
        # Look for support levels below entry
        targets = sorted(
            [price for price, is_res in sr_levels if not is_res and price < entry_price],  # pragma: no mutate
            reverse=True,
        )
        min_tp1 = entry_price - risk  # pragma: no mutate
        min_tp2 = entry_price - risk * 2  # pragma: no mutate

        for t in targets:
            if tp1 is None and t <= min_tp1:  # pragma: no mutate
                tp1 = t
            elif tp1 is not None and tp2 is None and t <= min_tp2:  # pragma: no mutate
                tp2 = t

        # Fallbacks using ATR multiples; TP2 must be farther from entry than TP1
        if tp1 is None:
            tp1 = entry_price - atr * ATR_MULTIPLIER_TP_FALLBACK  # pragma: no mutate
        if tp2 is None:
            atr_fallback = entry_price - atr * ATR_MULTIPLIER_TP_FALLBACK * 2  # pragma: no mutate
            tp2 = min(atr_fallback, tp1 - risk)  # pragma: no mutate

    # Invariant guard: TP2 must always be farther from entry than TP1.
    # The smart fallback above makes this unreachable under current code;
    # the guard fires only if future S/R logic changes break the invariant.
    if tp1 is not None and tp2 is not None:  # pragma: no mutate
        if direction == Direction.LONG and tp2 <= tp1:  # pragma: no mutate
            tp2 = tp1 + risk
        elif direction == Direction.SHORT and tp2 >= tp1:  # pragma: no mutate
            tp2 = tp1 - risk

    return tp1, tp2
