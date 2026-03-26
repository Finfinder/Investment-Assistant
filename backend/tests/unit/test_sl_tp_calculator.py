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
