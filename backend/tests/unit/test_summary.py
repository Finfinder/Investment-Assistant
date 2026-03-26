from app.core.models import IndicatorValue, MovingAverage, SignalType
from app.modules.technical_analysis.summary import calculate_summaries


def _make_indicators(signals: list[SignalType]) -> list[IndicatorValue]:
    return [IndicatorValue(name=f"IND_{i}", value=0.0, signal=s) for i, s in enumerate(signals)]


def _make_mas(sma_signals: list[SignalType], ema_signals: list[SignalType] | None = None) -> list[MovingAverage]:
    if ema_signals is None:
        ema_signals = sma_signals
    return [
        MovingAverage(period=(i + 1) * 10, sma_signal=ss, ema_signal=es)
        for i, (ss, es) in enumerate(zip(sma_signals, ema_signals, strict=False))
    ]


def test_all_buy_gives_strong_buy():
    inds = _make_indicators([SignalType.BUY] * 9)
    mas = _make_mas([SignalType.BUY] * 6)
    result = calculate_summaries(inds, mas)
    assert result.indicators_summary == SignalType.STRONG_BUY
    assert result.ma_summary == SignalType.STRONG_BUY
    assert result.overall_summary == SignalType.STRONG_BUY


def test_all_sell_gives_strong_sell():
    inds = _make_indicators([SignalType.SELL] * 9)
    mas = _make_mas([SignalType.SELL] * 6)
    result = calculate_summaries(inds, mas)
    assert result.indicators_summary == SignalType.STRONG_SELL
    assert result.ma_summary == SignalType.STRONG_SELL
    assert result.overall_summary == SignalType.STRONG_SELL


def test_mixed_gives_neutral():
    inds = _make_indicators([SignalType.BUY, SignalType.SELL, SignalType.NEUTRAL] * 3)
    mas = _make_mas([SignalType.BUY, SignalType.SELL, SignalType.NEUTRAL] * 2)
    result = calculate_summaries(inds, mas)
    assert result.overall_summary == SignalType.NEUTRAL


def test_counts_are_correct():
    inds = _make_indicators([SignalType.BUY, SignalType.SELL, SignalType.NEUTRAL])
    mas = _make_mas([SignalType.BUY], [SignalType.SELL])
    result = calculate_summaries(inds, mas)
    assert result.indicators_buy_count == 1
    assert result.indicators_sell_count == 1
    assert result.indicators_neutral_count == 1
    assert result.ma_buy_count == 1
    assert result.ma_sell_count == 1


def test_empty_inputs_gives_neutral():
    result = calculate_summaries([], [])
    assert result.overall_summary == SignalType.NEUTRAL
    assert result.overall_buy_count == 0


def test_strong_buy_threshold():
    """>=75% buy → strong_buy."""
    # 8 buy, 1 sell = 88.9% buy
    inds = _make_indicators([SignalType.BUY] * 8 + [SignalType.SELL])
    result = calculate_summaries(inds, [])
    assert result.indicators_summary == SignalType.STRONG_BUY


def test_buy_threshold():
    """>=55% buy but <75% → buy."""
    # 6 buy, 4 neutral = 60% buy
    inds = _make_indicators([SignalType.BUY] * 6 + [SignalType.NEUTRAL] * 4)
    result = calculate_summaries(inds, [])
    assert result.indicators_summary == SignalType.BUY
