"""Tests for strategy_generator/sl_tp_calculator.py"""

from datetime import UTC, datetime

from app.core.models import Direction, OHLCVData, PatternDetection
from app.modules.strategy_generator.sl_tp_calculator import calculate_atr, calculate_sl_tp


def _make_ohlcv(n: int = 20, base_price: float = 100.0) -> list[OHLCVData]:
    """Create N candles with known ATR-like ranges."""
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
            )
        )
        price += 1.0
    return data


def _make_sr(price: float, bullish: bool) -> PatternDetection:
    level_type = "support" if bullish else "resistance"
    return PatternDetection(
        pattern_type=f"S/R Level ({level_type})",
        confidence=0.7,
        description=f"{level_type.capitalize()} at {price:.2f} (3 touches)",
        bullish=bullish,
    )


def test_atr_calculation():
    """ATR for fixed H-L=3.0 candles should be ~3.0."""
    ohlcv = _make_ohlcv(20)
    atr = calculate_atr(ohlcv)
    assert 2.5 < atr < 3.5


def test_long_entry_with_sr():
    """Long: SL below nearest support, TP at resistance levels."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 120.0
    sr = [
        _make_sr(115.0, bullish=True),  # Support below
        _make_sr(130.0, bullish=False),  # Resistance above (TP1 candidate)
        _make_sr(145.0, bullish=False),  # Resistance further (TP2 candidate)
    ]

    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] < entry_price  # SL below entry
    assert result["tp1"] is not None
    assert result["tp1"] > entry_price  # TP1 above entry
    assert result["tp2"] is not None
    assert result["tp2"] > result["tp1"]  # TP2 further than TP1


def test_short_entry_with_sr():
    """Short: SL above nearest resistance, TP at support levels."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [
        _make_sr(105.0, bullish=True),  # Support below (TP1 candidate)
        _make_sr(95.0, bullish=True),  # Support further below (TP2 candidate)
        _make_sr(115.0, bullish=False),  # Resistance above
    ]

    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] > entry_price  # SL above entry
    assert result["tp1"] is not None
    assert result["tp1"] < entry_price  # TP1 below entry
    assert result["tp2"] is not None
    assert result["tp2"] < result["tp1"]  # TP2 farther from entry than TP1


def test_atr_fallback_no_sr():
    """Without S/R levels, SL/TP use ATR multiples."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 119.0  # Last close ≈ 120.0

    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] < entry_price
    assert result["tp1"] is not None
    assert result["tp1"] > entry_price
    assert result["tp2"] is not None
    assert result["tp2"] > result["tp1"]


def test_tight_sr_levels():
    """Tight S/R levels should still produce valid SL/TP."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 115.0
    sr = [
        _make_sr(114.5, bullish=True),  # Very close support
        _make_sr(115.5, bullish=False),  # Very close resistance
    ]

    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] < entry_price
    # TP may use ATR fallback if SR levels are too tight for R:R
    assert result["tp1"] is not None


def test_short_mixed_sr_atr_fallback():
    """Short: TP1 from S/R, TP2 from ATR fallback — reproduces the bug scenario.

    With a low ATR (like forex ~0.001) and one distant support as TP1,
    the raw ATR fallback for TP2 would land closer to entry than TP1.
    After the fix, TP2 must be farther from entry than TP1.
    """
    # Build OHLCV with very small range to produce low ATR (~0.001)
    data = []
    for i in range(20):
        ts = datetime(2024, 1, 1, hour=i % 24, tzinfo=UTC)
        base = 1.17 + i * 0.0001
        data.append(
            OHLCVData(
                timestamp=ts,
                open=base,
                high=base + 0.001,
                low=base - 0.0005,
                close=base + 0.0005,
            )
        )
    entry_price = 1.17
    # One support level far enough to be TP1 (matches screenshot scenario)
    sr = [_make_sr(1.15, bullish=True)]

    result = calculate_sl_tp(data, Direction.SHORT, entry_price, sr)

    assert result["tp1"] is not None
    assert result["tp1"] < entry_price  # TP1 below entry
    assert result["tp2"] is not None
    assert result["tp2"] < result["tp1"]  # TP2 farther from entry than TP1
    # TP2 must satisfy R:R >= 1:2 (at least 2x the risk distance from entry)
    risk = abs(entry_price - result["stop_loss"])
    assert result["tp2"] <= entry_price - risk * 2


def test_short_atr_fallback_no_sr():
    """Short without S/R: both TP1 and TP2 use ATR fallback, TP2 < TP1."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 119.0

    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] > entry_price  # SL above entry
    assert result["tp1"] is not None
    assert result["tp1"] < entry_price  # TP1 below entry
    assert result["tp2"] is not None
    assert result["tp2"] < result["tp1"]  # TP2 farther from entry than TP1


def test_long_mixed_sr_atr_fallback():
    """Long: TP1 from distant S/R, TP2 from ATR fallback — TP2 > TP1 enforced."""
    # Build OHLCV with very small range to produce low ATR
    data = []
    for i in range(20):
        ts = datetime(2024, 1, 1, hour=i % 24, tzinfo=UTC)
        base = 1.10 + i * 0.0001
        data.append(
            OHLCVData(
                timestamp=ts,
                open=base,
                high=base + 0.001,
                low=base - 0.0005,
                close=base + 0.0005,
            )
        )
    entry_price = 1.10
    # One resistance level far enough to be TP1 with low ATR
    sr = [_make_sr(1.12, bullish=False)]

    result = calculate_sl_tp(data, Direction.LONG, entry_price, sr)

    assert result["tp1"] is not None
    assert result["tp1"] > entry_price  # TP1 above entry
    assert result["tp2"] is not None
    assert result["tp2"] > result["tp1"]  # TP2 farther from entry than TP1


def test_short_entry_with_sr_levels():
    """SHORT: SL above nearest resistance, TP1/TP2 at support levels below (kills direction-flip mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [
        _make_sr(105.0, bullish=True),  # Support below (TP1 candidate)
        _make_sr(95.0, bullish=True),  # Support further below (TP2 candidate)
        _make_sr(115.0, bullish=False),  # Resistance above (SL candidate)
    ]

    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)

    # SL must be above entry (resistance + buffer)
    assert result["stop_loss"] is not None
    assert result["stop_loss"] > entry_price
    # TP1/TP2 must be below entry (support levels)
    assert result["tp1"] is not None
    assert result["tp1"] < entry_price
    assert result["tp2"] is not None
    assert result["tp2"] < result["tp1"]


def test_long_sl_at_support_below_entry():
    """LONG: SL uses nearest support below entry minus ATR buffer (kills is_res/comparison mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 120.0
    sr = [_make_sr(115.0, bullish=True)]  # Support below

    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] < entry_price
    # SL should be near support minus a small ATR buffer
    assert result["stop_loss"] < 115.0


def test_short_sl_at_resistance_above_entry():
    """SHORT: SL uses nearest resistance above entry plus ATR buffer (kills is_res/comparison mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [_make_sr(115.0, bullish=False)]  # Resistance above

    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)

    assert result["stop_loss"] is not None
    assert result["stop_loss"] > entry_price
    # SL should be near resistance plus a small ATR buffer
    assert result["stop_loss"] > 115.0


def test_sr_level_at_exactly_entry_excluded():
    """S/R level exactly at entry price is NOT a candidate (kills <= / >= mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    # Support exactly at entry must be excluded for LONG (needs price < entry)
    sr = [_make_sr(110.0, bullish=True)]

    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)

    # No valid support below → SL falls back to ATR multiple below entry
    assert result["stop_loss"] is not None
    assert result["stop_loss"] < entry_price


def test_extract_sr_prices_resistance_flag():
    """_extract_sr_prices maps bullish=False → is_resistance True (kills not p.bullish mutants)."""
    from app.modules.strategy_generator.sl_tp_calculator import _extract_sr_prices

    sr = [
        _make_sr(115.0, bullish=True),  # support → is_resistance False
        _make_sr(125.0, bullish=False),  # resistance → is_resistance True
    ]
    extracted = _extract_sr_prices(sr)
    assert (115.0, False) in extracted
    assert (125.0, True) in extracted


def test_atr_short_ohlcv_returns_zero():
    """ATR with fewer than 2 candles returns 0.0 (kills < 3 / return 1.0 mutants)."""
    from app.modules.strategy_generator.sl_tp_calculator import calculate_atr

    single = [
        OHLCVData(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
        )
    ]
    assert calculate_atr(single) == 0.0


def test_atr_uses_last_period_values():
    """ATR uses only the last `period` TR values (kills [-period:] → [+period:] mutant)."""
    from app.modules.strategy_generator.sl_tp_calculator import calculate_atr

    # 30 candles with constant TR=3.0; period default 14 → ATR must be 3.0
    ohlcv = _make_ohlcv(30, base_price=100.0)
    atr = calculate_atr(ohlcv, period=14)
    assert abs(atr - 3.0) < 1e-6


def test_tp_invariants_long():
    """LONG: TP2 is always farther from entry than TP1 (kills invariant-guard mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 120.0
    sr = [
        _make_sr(130.0, bullish=False),
        _make_sr(140.0, bullish=False),
    ]
    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)
    assert result["tp1"] is not None
    assert result["tp2"] is not None
    assert result["tp2"] > result["tp1"] > entry_price


def test_tp_invariants_short():
    """SHORT: TP2 is always farther from entry than TP1 (kills invariant-guard mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [
        _make_sr(105.0, bullish=True),
        _make_sr(95.0, bullish=True),
    ]
    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)
    assert result["tp1"] is not None
    assert result["tp2"] is not None
    assert result["tp2"] < result["tp1"] < entry_price


def test_atr_two_candles_nonzero():
    """ATR with exactly 2 candles must compute (kills len<=2 / len<3 / range(2,len) mutants)."""
    from app.modules.strategy_generator.sl_tp_calculator import calculate_atr

    ohlcv = _make_ohlcv(2, base_price=100.0)
    atr = calculate_atr(ohlcv)
    assert atr != 0.0  # guard `len(ohlcv) < 2` must NOT trigger for 2 candles


def test_long_sl_no_sr_uses_atr_multiplier():
    """LONG without S/R: SL = entry - 1.5*ATR (kills atr/ATR_MULTIPLIER_SL fallback mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 119.0  # last close ~120, ATR ~3.0
    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price)  # no sr
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: 119 - 1.5*3 = 114.5. Mutant (atr/1.5): 119 - 2 = 117 (> 116).
    assert sl < entry_price - 3.0


def test_long_sl_support_at_exactly_entry_excluded():
    """LONG: support exactly at entry is excluded → SL uses ATR fallback (kills `<=` mutant)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [_make_sr(110.0, bullish=True)]  # support exactly at entry
    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: support excluded → SL = 110 - 1.5*3 = 105.5. Mutant (`<=`): 110 - 0.5*3 = 108.5.
    assert sl < entry_price - 3.0


def test_long_sl_buffer_below_support():
    """LONG: SL = support - 0.5*ATR (kills atr/0.5 and atr*1.5 buffer mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 120.0
    sr = [_make_sr(115.0, bullish=True)]  # support below
    result = calculate_sl_tp(ohlcv, Direction.LONG, entry_price, sr)
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: 115 - 1.5 = 113.5. Mutant(/0.5): 115 - 6 = 109. Mutant(*1.5): 115 - 4.5 = 110.5.
    assert sl > 115.0 - 2.0 * 3.0
    assert sl > 115.0 - 1.0 * 3.0


def test_short_sl_resistance_at_exactly_entry_excluded():
    """SHORT: resistance exactly at entry is excluded → SL uses ATR fallback (kills `>=` mutant)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [_make_sr(110.0, bullish=False)]  # resistance exactly at entry
    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: resistance excluded → SL = 110 + 1.5*3 = 114.5. Mutant (`>=`): 110 + 0.5*3 = 111.5.
    assert sl > entry_price + 3.0


def test_short_sl_support_above_entry_excluded():
    """SHORT: a support (is_res=False) above entry is NOT a resistance (kills `is_res or` mutant)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [_make_sr(115.0, bullish=True)]  # support above entry
    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: excluded → SL = 114.5. Mutant (`or`): included → SL = 115 + 1.5 = 116.5.
    assert sl < entry_price + 6.0


def test_short_sl_buffer_above_resistance():
    """SHORT: SL = resistance + 0.5*ATR (kills atr/0.5 and atr*1.5 buffer mutants)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 110.0
    sr = [_make_sr(115.0, bullish=False)]  # resistance above
    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price, sr)
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: 115 + 1.5 = 116.5. Mutant(/0.5): 115 + 6 = 121. Mutant(*1.5): 115 + 4.5 = 119.5.
    assert sl < 115.0 + 2.0 * 3.0
    assert sl < 115.0 + 1.0 * 3.0


def test_short_sl_no_sr_uses_atr_multiplier():
    """SHORT without S/R: SL = entry + 1.5*ATR (kills atr/ATR_MULTIPLIER_SL fallback mutant)."""
    ohlcv = _make_ohlcv(20, base_price=100.0)
    entry_price = 101.0
    result = calculate_sl_tp(ohlcv, Direction.SHORT, entry_price)  # no sr
    sl = result["stop_loss"]
    assert sl is not None
    # Normal: 101 + 1.5*3 = 105.5. Mutant (atr/1.5): 101 + 2 = 103.
    assert sl > entry_price + 3.0
