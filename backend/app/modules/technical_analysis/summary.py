from app.core.models import IndicatorValue, MovingAverage, SignalSummary, SignalType


def calculate_summaries(
    indicators: list[IndicatorValue],
    moving_averages: list[MovingAverage],
) -> SignalSummary:
    """Aggregate indicator and moving-average signals into a summary.

    MA Summary counts each SMA and EMA signal (up to 12 signals for 6 periods).
    Indicators Summary counts each indicator signal.
    Overall combines both groups.

    Thresholds:
      strong_buy  ≥75% buy
      buy         ≥55% buy
      sell        ≥55% sell
      strong_sell ≥75% sell
      neutral     otherwise
    """
    # --- MA signals ---
    ma_buy = 0
    ma_sell = 0
    ma_neutral = 0
    for ma in moving_averages:
        ma_buy, ma_sell, ma_neutral = _tally(ma.sma_signal, ma_buy, ma_sell, ma_neutral)
        ma_buy, ma_sell, ma_neutral = _tally(ma.ema_signal, ma_buy, ma_sell, ma_neutral)

    ma_total = ma_buy + ma_sell + ma_neutral
    ma_summary = _overall_signal(ma_buy, ma_sell, ma_total)

    # --- Indicator signals ---
    ind_buy = 0
    ind_sell = 0
    ind_neutral = 0
    for ind in indicators:
        ind_buy, ind_sell, ind_neutral = _tally(ind.signal, ind_buy, ind_sell, ind_neutral)

    ind_total = ind_buy + ind_sell + ind_neutral
    ind_summary = _overall_signal(ind_buy, ind_sell, ind_total)

    # --- Overall ---
    all_buy = ma_buy + ind_buy
    all_sell = ma_sell + ind_sell
    all_neutral = ma_neutral + ind_neutral
    all_total = all_buy + all_sell + all_neutral
    overall = _overall_signal(all_buy, all_sell, all_total)

    return SignalSummary(
        ma_summary=ma_summary,
        ma_buy_count=ma_buy,
        ma_sell_count=ma_sell,
        ma_neutral_count=ma_neutral,
        indicators_summary=ind_summary,
        indicators_buy_count=ind_buy,
        indicators_sell_count=ind_sell,
        indicators_neutral_count=ind_neutral,
        overall_summary=overall,
        overall_buy_count=all_buy,
        overall_sell_count=all_sell,
        overall_neutral_count=all_neutral,
    )


def _tally(signal: SignalType, buy: int, sell: int, neutral: int) -> tuple[int, int, int]:
    """Classify a signal into one of the three buckets."""
    if signal in (SignalType.BUY, SignalType.STRONG_BUY):
        return buy + 1, sell, neutral
    if signal in (SignalType.SELL, SignalType.STRONG_SELL):
        return buy, sell + 1, neutral
    return buy, sell, neutral + 1


def _overall_signal(buy: int, sell: int, total: int) -> SignalType:
    if total == 0:
        return SignalType.NEUTRAL
    buy_pct = buy / total
    sell_pct = sell / total
    if buy_pct >= 0.75:
        return SignalType.STRONG_BUY
    if buy_pct >= 0.55:
        return SignalType.BUY
    if sell_pct >= 0.75:
        return SignalType.STRONG_SELL
    if sell_pct >= 0.55:
        return SignalType.SELL
    return SignalType.NEUTRAL
