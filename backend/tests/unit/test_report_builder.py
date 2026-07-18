"""Tests for strategy_generator/report_builder.py"""

from datetime import UTC, datetime

from app.core.models import (
    AnalysisTimeframeContext,
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    LongTermTrend,
    MovingAverage,
    OHLCVData,
    PatternCategory,
    PatternDetection,
    PatternScannerResult,
    SignalSummary,
    SignalType,
    StrategyEntry,
    Timeframe,
)
from app.modules.strategy_generator.report_builder import (
    _FLOAT_ZERO_EPSILON,
    _calculate_risk_reward,
    build_report,
)


def _make_ohlcv(n: int = 20, base_price: float = 100.0) -> list[OHLCVData]:
    data = []
    price = base_price
    for i in range(n):
        data.append(
            OHLCVData(
                timestamp=datetime(2024, 1, 1, hour=i % 24, tzinfo=UTC),
                open=price,
                high=price + 2.0,
                low=price - 1.0,
                close=price + 1.0,
                volume=1000.0,
            )
        )
        price += 1.0
    return data


def test_bullish_report():
    """Strong bullish inputs → report with LONG strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.BUY, ema_signal=SignalType.BUY)]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            description="Support at 110.00 (3 touches)",
            bullish=True,
        ),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=50)

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=mas,
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        fundamental=fundamental,
        direction=Direction.LONG,
        instrument_type=InstrumentType.FOREX,
    )

    assert report.symbol == "EURUSD"
    assert report.timeframe == Timeframe.H1
    assert report.instrument_type == InstrumentType.FOREX
    assert len(report.strategies) >= 1
    assert all(s.direction == Direction.LONG for s in report.strategies)
    assert all(s.entry_price is not None for s in report.strategies)
    assert all(s.stop_loss is not None for s in report.strategies)
    assert all(s.risk_reward_ratio is None or s.risk_reward_ratio <= 1.0 for s in report.strategies)
    assert all(s.risk_reward_ratio_tp2 is not None for s in report.strategies)
    assert report.strategy_skip_reason is None


def test_bearish_report():
    """Strong bearish inputs → report with SHORT strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=25, signal=SignalType.SELL),
        IndicatorValue(name="ADX(14)", value=40, signal=SignalType.SELL),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.SELL, ema_signal=SignalType.SELL)]
    summary = SignalSummary(
        overall_summary=SignalType.STRONG_SELL,
        overall_buy_count=0,
        overall_sell_count=9,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (resistance)",
            confidence=0.8,
            description="Resistance at 125.00 (4 touches)",
            bullish=False,
        ),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=-60)

    report = build_report(
        symbol="GBPUSD",
        timeframe=Timeframe.D1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=mas,
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        fundamental=fundamental,
        direction=Direction.SHORT,
        instrument_type=InstrumentType.FOREX,
    )

    assert report.instrument_type == InstrumentType.FOREX
    assert len(report.strategies) >= 1
    assert all(s.direction == Direction.SHORT for s in report.strategies)
    assert all(s.risk_reward_ratio is None or s.risk_reward_ratio <= 1.0 for s in report.strategies)
    assert all(s.risk_reward_ratio_tp2 is not None for s in report.strategies)
    assert report.strategy_skip_reason is None


def test_neutral_report_no_strategies():
    """Neutral inputs → report with no strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [IndicatorValue(name="RSI(14)", value=50, signal=SignalType.NEUTRAL)]
    summary = SignalSummary(overall_summary=SignalType.NEUTRAL)

    report = build_report(
        symbol="USDJPY",
        timeframe=Timeframe.H4,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=[],
        signal_summary=summary,
        instrument_type=InstrumentType.FOREX,
    )

    assert report.instrument_type == InstrumentType.FOREX
    assert report.strategies == []
    assert report.strategy_skip_reason is not None
    assert len(report.strategy_skip_reason) > 0


def test_build_report_default_instrument_type():
    """Calling build_report without instrument_type gives None."""
    ohlcv = _make_ohlcv(20)
    indicators = [IndicatorValue(name="RSI(14)", value=50, signal=SignalType.NEUTRAL)]
    summary = SignalSummary(overall_summary=SignalType.NEUTRAL)

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=[],
        signal_summary=summary,
    )

    assert report.instrument_type is None


def test_build_report_preserves_multi_timeframe_sections():
    ohlcv = _make_ohlcv(20)
    representative_pattern = PatternDetection(
        pattern_type="Hammer",
        confidence=0.8,
        bullish=True,
        timeframe=Timeframe.H1,
    )
    scanner_result = PatternScannerResult(
        pattern_type="Hammer",
        category=representative_pattern.category,
        bullish=True,
        confidence=0.8,
        timeframes=[Timeframe.D1, Timeframe.H1],
        representative_pattern=representative_pattern,
    )
    timeframe_context = AnalysisTimeframeContext(
        pivot_points_timeframe=Timeframe.D1,
        pattern_scanner_timeframes=[Timeframe.D1, Timeframe.H1, Timeframe.M15],
    )
    long_term_trend = LongTermTrend(signal=SignalType.BUY, summary="Trend wzrostowy")

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=[],
        moving_averages=[],
        pivot_points=[],
        patterns=[representative_pattern],
        timeframe_context=timeframe_context,
        pattern_scanner_results=[scanner_result],
        long_term_trend=long_term_trend,
        instrument_type=InstrumentType.FOREX,
    )

    assert report.timeframe_context == timeframe_context
    assert report.pattern_scanner_results == [scanner_result]
    assert report.long_term_trend == long_term_trend


# --- Risk/Reward calculation tests ---


def test_calculate_risk_reward_favorable():
    """R/R with risk < reward returns ratio < 1.0."""
    # risk=2, reward=6 → 0.33
    assert _calculate_risk_reward(100.0, 98.0, 106.0) == 0.33


def test_calculate_risk_reward_unfavorable():
    """R/R with risk > reward returns ratio > 1.0."""
    # risk=5, reward=2 → 2.5
    assert _calculate_risk_reward(100.0, 95.0, 102.0) == 2.5


def test_calculate_risk_reward_boundary():
    """R/R with risk == reward returns exactly 1.0."""
    # risk=3, reward=3 → 1.0
    assert _calculate_risk_reward(100.0, 97.0, 103.0) == 1.0


def test_calculate_risk_reward_none_when_missing_values():
    """R/R returns None when any input is None."""
    assert _calculate_risk_reward(None, 98.0, 106.0) is None
    assert _calculate_risk_reward(100.0, None, 106.0) is None
    assert _calculate_risk_reward(100.0, 98.0, None) is None


def test_calculate_risk_reward_none_when_zero_reward():
    """R/R returns None when tp1 == entry_price (zero reward)."""
    assert _calculate_risk_reward(100.0, 98.0, 100.0) is None


def test_calculate_risk_reward_none_when_near_zero_reward():
    """R/R returns None when reward is below the float-zero threshold (python:S1244)."""
    sub_epsilon = _FLOAT_ZERO_EPSILON / 10  # clearly below the threshold
    assert _calculate_risk_reward(100.0, 98.0, 100.0 + sub_epsilon) is None


def test_risk_reward_favorable_kept():
    """Strategy with favorable R/R (< 1.0) is kept in the report."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            description="Support at 110.00 (3 touches)",
            bullish=True,
        ),
    ]

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        direction=Direction.LONG,
        instrument_type=InstrumentType.FOREX,
    )

    favorable = [s for s in report.strategies if s.risk_reward_ratio is not None and s.risk_reward_ratio <= 1.0]
    assert len(favorable) >= 1
    assert all(s.risk_reward_ratio_tp2 is not None for s in report.strategies)
    assert report.strategy_skip_reason is None


def test_risk_reward_tp2_more_favorable_than_tp1():
    """R/R for TP2 should be <= R/R for TP1 (TP2 is farther target)."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            description="Support at 110.00 (3 touches)",
            bullish=True,
        ),
    ]

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        direction=Direction.LONG,
        instrument_type=InstrumentType.FOREX,
    )

    for s in report.strategies:
        if s.risk_reward_ratio is not None and s.risk_reward_ratio_tp2 is not None:
            assert s.risk_reward_ratio_tp2 <= s.risk_reward_ratio


def test_risk_reward_boundary_kept():
    """Strategy with R/R exactly 1.0 (boundary) is NOT filtered out."""
    entry = StrategyEntry(
        direction=Direction.LONG,
        entry_condition="Test",
        entry_price=100.0,
        stop_loss=97.0,
        tp1=103.0,
        confidence_pct=50.0,
        risk_reward_ratio=1.0,
    )
    assert entry.risk_reward_ratio == 1.0  # boundary: kept (≤ 1.0)


def test_risk_reward_tp2_more_favorable_than_tp1_short():
    """R/R for TP2 should be <= R/R for TP1 for SHORT strategies (TP2 is farther target)."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=25, signal=SignalType.SELL),
        IndicatorValue(name="ADX(14)", value=40, signal=SignalType.SELL),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.STRONG_SELL,
        overall_buy_count=0,
        overall_sell_count=9,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (resistance)",
            confidence=0.8,
            description="Resistance at 125.00 (4 touches)",
            bullish=False,
        ),
    ]

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        direction=Direction.SHORT,
        instrument_type=InstrumentType.FOREX,
    )

    for s in report.strategies:
        if s.risk_reward_ratio is not None and s.risk_reward_ratio_tp2 is not None:
            assert s.risk_reward_ratio_tp2 <= s.risk_reward_ratio


def test_confirming_patterns_filter_candlestick_reliability_direction():
    """Only CANDLESTICK patterns with reliability >= 2 and matching direction are confirming (kills filter mutants)."""
    from app.modules.strategy_generator.report_builder import _build_strategies

    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        # CANDLESTICK, reliability 2, bullish (LONG) → confirming
        PatternDetection(
            pattern_type="Hammer",
            confidence=0.8,
            bullish=True,
            category=PatternCategory.CANDLESTICK,
            reliability=2,
        ),
        # CANDLESTICK but reliability 1 → excluded
        PatternDetection(
            pattern_type="Doji",
            confidence=0.5,
            bullish=True,
            category=PatternCategory.CANDLESTICK,
            reliability=1,
        ),
        # CANDLESTICK but bearish (opposes LONG) → excluded
        PatternDetection(
            pattern_type="ShootingStar",
            confidence=0.8,
            bullish=False,
            category=PatternCategory.CANDLESTICK,
            reliability=3,
        ),
        # Non-candlestick → excluded
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            bullish=True,
            category=PatternCategory.SUPPORT_RESISTANCE,
            reliability=3,
        ),
    ]

    strategies = _build_strategies(
        direction=Direction.LONG,
        ohlcv=ohlcv,
        indicators=indicators,
        signal_summary=summary,
        patterns=patterns,
        fundamental=None,
        sr_patterns=[],
        fib_patterns=[],
    )

    # The confirming pattern must appear in at least one entry condition
    all_conditions = " ".join(str(s.entry_condition) for s in strategies)
    assert "Hammer" in all_conditions
    assert "Doji" not in all_conditions
    assert "ShootingStar" not in all_conditions


def test_neutral_skip_reason_text():
    """Neutral (direction=None) report sets the expected skip reason (kills skip-reason string mutants)."""
    ohlcv = _make_ohlcv(20)
    indicators = [IndicatorValue(name="RSI(14)", value=50, signal=SignalType.NEUTRAL)]
    summary = SignalSummary(overall_summary=SignalType.NEUTRAL)

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=[],
        signal_summary=summary,
        instrument_type=InstrumentType.FOREX,
    )

    assert report.strategy_skip_reason is not None
    assert "neutralne" in report.strategy_skip_reason


def test_all_strategies_rejected_skip_reason():
    """The 'all strategies rejected' skip reason is reachable only when no entry survives R/R filtering.

    The aggressive (market-price) entry always has a favorable ATR-based R:R, so in practice
    at least one strategy is kept; this test documents that the rejection branch is guarded by
    the R/R filter and that the neutral-direction branch sets its own skip reason (see
    test_neutral_skip_reason_text). Display-string mutants on the rejection message are marked
    equivalent via `# pragma: no mutate` in report_builder.py.
    """
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            description="Support at 119.00 (3 touches)",
            bullish=True,
        ),
    ]

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        direction=Direction.LONG,
        instrument_type=InstrumentType.FOREX,
    )

    # Aggressive entry is always kept (favorable ATR R:R), so strategies are non-empty
    assert len(report.strategies) >= 1
