"""Tests for strategy_generator/entry_calculator.py"""

from datetime import UTC, datetime

from app.core.models import Direction, OHLCVData, PatternDetection
from app.modules.strategy_generator.entry_calculator import calculate_entry_points


def _make_ohlcv(close: float = 1.1000) -> list[OHLCVData]:
    return [OHLCVData(timestamp=datetime(2024, 1, 1, tzinfo=UTC), open=1.0900, high=1.1100, low=1.0800, close=close)]


def _make_sr(price: float, bullish: bool) -> PatternDetection:
    level_type = "support" if bullish else "resistance"
    return PatternDetection(
        pattern_type=f"S/R Level ({level_type})",
        confidence=0.7,
        description=f"{level_type.capitalize()} at {price:.5f} (3 touches, 2.0% from current price)",
        bullish=bullish,
    )


def _make_fib(price: float, bullish: bool) -> PatternDetection:
    direction = "Uptrend" if bullish else "Downtrend"
    return PatternDetection(
        pattern_type="Fibonacci 38.2%",
        confidence=0.6,
        description=f"{direction} retracement 38.2% at {price:.5f}",
        bullish=bullish,
    )


def test_aggressive_entry_long():
    """Aggressive long entry should be at current market price."""
    ohlcv = _make_ohlcv(1.1000)
    entries = calculate_entry_points(ohlcv, Direction.LONG)
    assert len(entries) >= 1

    aggressive = entries[0]
    assert aggressive["type"] == "aggressive"
    assert aggressive["price"] == 1.1000
    assert "long" in str(aggressive["condition"]).lower()


def test_aggressive_entry_short():
    """Aggressive short entry should be at current market price."""
    ohlcv = _make_ohlcv(1.1000)
    entries = calculate_entry_points(ohlcv, Direction.SHORT)
    assert len(entries) >= 1

    aggressive = entries[0]
    assert aggressive["type"] == "aggressive"
    assert aggressive["price"] == 1.1000
    assert "short" in str(aggressive["condition"]).lower()


def test_conservative_entry_at_support():
    """Long entry should find nearest support level below current price."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [
        _make_sr(1.0800, bullish=True),  # Support below
        _make_sr(1.1200, bullish=False),  # Resistance above
    ]
    entries = calculate_entry_points(ohlcv, Direction.LONG, support_resistance=sr)

    conservative = [e for e in entries if e["type"] == "conservative"]
    assert len(conservative) == 1
    assert conservative[0]["price"] == 1.08000
    assert "condition" in conservative[0]  # kills XXconditionXX key mutant (138)


def test_conservative_entry_at_resistance():
    """Short entry should find nearest resistance above current price."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [
        _make_sr(1.0800, bullish=True),
        _make_sr(1.1200, bullish=False),
    ]
    entries = calculate_entry_points(ohlcv, Direction.SHORT, support_resistance=sr)

    conservative = [e for e in entries if e["type"] == "conservative"]
    assert len(conservative) == 1
    assert conservative[0]["price"] == 1.12000
    assert "condition" in conservative[0]  # kills XXconditionXX key mutant (144)


def test_conservative_entry_at_fibonacci():
    """Should find Fibonacci level for conservative entry."""
    ohlcv = _make_ohlcv(1.1000)
    fib = [_make_fib(1.0850, bullish=True)]
    entries = calculate_entry_points(ohlcv, Direction.LONG, fibonacci_levels=fib)

    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert len(fib_entries) == 1
    assert fib_entries[0]["price"] == 1.085


def test_empty_ohlcv():
    """Empty OHLCV → no entries."""
    assert calculate_entry_points([], Direction.LONG) == []


def _make_candlestick_pattern(name: str, bullish: bool, reliability: int) -> PatternDetection:
    from app.core.models import PatternCategory

    return PatternDetection(
        pattern_type=name,
        confidence=0.7,
        bullish=bullish,
        category=PatternCategory.CANDLESTICK,
        reliability=reliability,
    )


def test_confirming_patterns_appended_to_entry_condition():
    """Entry condition powinien zawierać nazwy formacji ★★+ gdy przekazano confirming_patterns."""
    ohlcv = _make_ohlcv(1.1000)
    confirming = [
        _make_candlestick_pattern("Hammer", bullish=True, reliability=2),
        _make_candlestick_pattern("Three White Soldiers", bullish=True, reliability=3),
    ]
    entries = calculate_entry_points(ohlcv, Direction.LONG, confirming_patterns=confirming)

    assert len(entries) >= 1
    condition = str(entries[0]["condition"])
    assert "Potwierdzone:" in condition
    assert "Hammer" in condition
    assert "★★" in condition
    assert "Three White Soldiers" in condition
    assert "★★★" in condition


def test_no_confirming_patterns_no_suffix():
    """Bez formacji ★★+ entry_condition nie zawiera 'Potwierdzone'."""
    ohlcv = _make_ohlcv(1.1000)
    entries = calculate_entry_points(ohlcv, Direction.LONG, confirming_patterns=[])

    condition = str(entries[0]["condition"])
    assert "Potwierdzone" not in condition


def test_backward_compatibility_no_confirming_param():
    """Wywołanie bez parametru confirming_patterns działa jak przed zmianą."""
    ohlcv = _make_ohlcv(1.1000)
    entries = calculate_entry_points(ohlcv, Direction.LONG)

    assert len(entries) >= 1
    condition = str(entries[0]["condition"])
    assert "Potwierdzone" not in condition


def test_short_conservative_entry_at_resistance():
    """SHORT entry should find nearest resistance above current price (kills direction-flip mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [
        _make_sr(1.0800, bullish=True),
        _make_sr(1.1200, bullish=False),
    ]
    entries = calculate_entry_points(ohlcv, Direction.SHORT, support_resistance=sr)

    conservative = [e for e in entries if e["type"] == "conservative"]
    assert len(conservative) == 1
    assert conservative[0]["price"] == 1.12000


def test_short_conservative_entry_at_resistance_above():
    """SHORT conservative entry should pick nearest resistance above current price (kills direction-flip mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [
        _make_sr(1.0800, bullish=True),
        _make_sr(1.1200, bullish=False),
    ]
    entries = calculate_entry_points(ohlcv, Direction.SHORT, support_resistance=sr)

    conservative = [e for e in entries if e["type"] == "conservative"]
    assert len(conservative) == 1
    assert conservative[0]["price"] == 1.12000


def test_short_conservative_entry_at_fibonacci():
    """SHORT entry should find Fibonacci level above current price."""
    ohlcv = _make_ohlcv(1.1000)
    fib = [_make_fib(1.1150, bullish=False)]
    entries = calculate_entry_points(ohlcv, Direction.SHORT, fibonacci_levels=fib)

    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert len(fib_entries) == 1
    assert fib_entries[0]["price"] == 1.115


def test_short_confirming_patterns_appended():
    """SHORT entry condition should include confirming candlestick patterns (kills suffix mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    confirming = [
        _make_candlestick_pattern("ShootingStar", bullish=False, reliability=2),
        _make_candlestick_pattern("Three Black Crows", bullish=False, reliability=3),
    ]
    entries = calculate_entry_points(ohlcv, Direction.SHORT, confirming_patterns=confirming)

    condition = str(entries[0]["condition"])
    assert "Potwierdzone:" in condition
    assert "ShootingStar" in condition
    assert "★★" in condition


def test_sr_entry_uses_condition_key():
    """Conservative S/R entry must store under 'condition' key (kills XXconditionXX/None mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [_make_sr(1.0800, bullish=True)]
    entries = calculate_entry_points(ohlcv, Direction.LONG, support_resistance=sr)

    conservative = [e for e in entries if e["type"] == "conservative"]
    assert "condition" in conservative[0]
    assert conservative[0]["condition"] is not None


def test_fib_entry_uses_condition_key():
    """Conservative Fibonacci entry must store under 'condition' key."""
    ohlcv = _make_ohlcv(1.1000)
    fib = [_make_fib(1.0850, bullish=True)]
    entries = calculate_entry_points(ohlcv, Direction.LONG, fibonacci_levels=fib)

    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert "condition" in fib_entries[0]
    assert fib_entries[0]["condition"] is not None


def test_sr_level_at_exactly_current_price_excluded():
    """S/R level exactly at current price is NOT a candidate (kills <= / >= mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    # Support exactly at current price must be excluded for LONG (needs price < current)
    sr = [_make_sr(1.1000, bullish=True)]
    entries = calculate_entry_points(ohlcv, Direction.LONG, support_resistance=sr)
    conservative = [e for e in entries if e["type"] == "conservative"]
    assert conservative == []


def test_sr_pattern_without_price_skipped():
    """S/R pattern whose description has no price is skipped (kills continue→break mutants)."""
    ohlcv = _make_ohlcv(1.1000)
    no_price = PatternDetection(
        pattern_type="S/R Level (support)",
        confidence=0.7,
        description="Support without a price level",
        bullish=True,
    )
    sr_with_price = _make_sr(1.0800, bullish=True)
    entries = calculate_entry_points(ohlcv, Direction.LONG, support_resistance=[no_price, sr_with_price])
    conservative = [e for e in entries if e["type"] == "conservative"]
    # The valid support is still found despite the no-price pattern
    assert len(conservative) == 1
    assert conservative[0]["price"] == 1.08000


def test_fib_pattern_without_price_skipped():
    """Fibonacci pattern whose description has no price is skipped."""
    ohlcv = _make_ohlcv(1.1000)
    no_price = PatternDetection(
        pattern_type="Fibonacci 38.2%",
        confidence=0.6,
        description="Retracement without a price",
        bullish=True,
    )
    fib_with_price = _make_fib(1.0850, bullish=True)
    entries = calculate_entry_points(ohlcv, Direction.LONG, fibonacci_levels=[no_price, fib_with_price])
    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert len(fib_entries) == 1
    assert fib_entries[0]["price"] == 1.085


def test_empty_confirming_returns_empty_string():
    """_format_confirming_patterns with empty list returns '' (kills return 'XXXX' mutant)."""
    from app.modules.strategy_generator.entry_calculator import _format_confirming_patterns

    assert _format_confirming_patterns([]) == ""


def test_sr_support_at_exactly_entry_excluded_long():
    """LONG: S/R support exactly at entry is excluded (kills `<=` mutant on level_price < current)."""
    ohlcv = _make_ohlcv(1.1000)
    sr = [_make_sr(1.1000, bullish=True)]  # support exactly at entry
    entries = calculate_entry_points(ohlcv, Direction.LONG, support_resistance=sr)
    conservative = [e for e in entries if e["type"] == "conservative"]
    assert conservative == []


def test_fib_support_at_exactly_entry_excluded_long():
    """LONG: Fibonacci support exactly at entry is excluded (kills `<=` mutant)."""
    ohlcv = _make_ohlcv(1.1000)
    fib = [_make_fib(1.1000, bullish=True)]  # support exactly at entry
    entries = calculate_entry_points(ohlcv, Direction.LONG, fibonacci_levels=fib)
    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert fib_entries == []


def test_fib_resistance_at_exactly_entry_excluded_short():
    """SHORT: Fibonacci resistance exactly at entry is excluded (kills `>=` mutant)."""
    ohlcv = _make_ohlcv(1.1000)
    fib = [_make_fib(1.1000, bullish=False)]  # resistance exactly at entry
    entries = calculate_entry_points(ohlcv, Direction.SHORT, fibonacci_levels=fib)
    fib_entries = [e for e in entries if e["type"] == "conservative_fib"]
    assert fib_entries == []
