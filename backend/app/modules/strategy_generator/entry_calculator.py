"""Entry point calculator — aggressive and conservative entry scenarios."""

import re

from app.core.models import Direction, OHLCVData, PatternDetection

_PRICE_RE = re.compile(r"(?:at|Level|level)\s+(\d+\.?\d*)")


def calculate_entry_points(
    ohlcv: list[OHLCVData],
    direction: Direction,
    support_resistance: list[PatternDetection] | None = None,
    fibonacci_levels: list[PatternDetection] | None = None,
) -> list[dict[str, object]]:
    """Calculate entry points for the given direction.

    Returns a list of entry scenarios:
    - Aggressive: market price entry
    - Conservative: entry at nearest S/R or Fibonacci level

    Each entry dict has: type, price, condition (descriptive text).
    """
    if not ohlcv:
        return []

    current_price = ohlcv[-1].close
    entries: list[dict[str, object]] = []

    # Aggressive entry — at current market price
    if direction == Direction.LONG:
        entries.append(
            {
                "type": "aggressive",
                "price": current_price,
                "condition": f"Wejscie po cenie rynkowej {current_price:.5f} (long)",
            }
        )
    else:
        entries.append(
            {
                "type": "aggressive",
                "price": current_price,
                "condition": f"Wejscie po cenie rynkowej {current_price:.5f} (short)",
            }
        )

    # Conservative entry — at nearest S/R level
    sr_levels = support_resistance or []
    sr_entry = _find_conservative_sr_entry(current_price, direction, sr_levels)
    if sr_entry:
        entries.append(sr_entry)

    # Conservative entry — at Fibonacci level
    fib_levels = fibonacci_levels or []
    fib_entry = _find_conservative_fib_entry(current_price, direction, fib_levels)
    if fib_entry:
        entries.append(fib_entry)

    return entries


def _find_conservative_sr_entry(
    current_price: float,
    direction: Direction,
    sr_patterns: list[PatternDetection],
) -> dict[str, object] | None:
    """Find entry at nearest support (long) or resistance (short) level."""
    candidates: list[float] = []
    for p in sr_patterns:
        # Extract price from description (format: "... at {price} ...")
        level_price = _extract_price_from_description(p.description)
        if level_price is None:
            continue

        if (direction == Direction.LONG and level_price < current_price) or (
            direction == Direction.SHORT and level_price > current_price
        ):
            candidates.append(level_price)

    if not candidates:
        return None

    if direction == Direction.LONG:
        # Nearest support below current price
        best = max(candidates)
        return {
            "type": "conservative",
            "price": best,
            "condition": f"Wejscie przy odbiciu od wsparcia {best:.5f}",
        }
    # Nearest resistance above current price
    best = min(candidates)
    return {
        "type": "conservative",
        "price": best,
        "condition": f"Wejscie przy odbiciu od oporu {best:.5f}",
    }


def _find_conservative_fib_entry(
    current_price: float,
    direction: Direction,
    fib_patterns: list[PatternDetection],
) -> dict[str, object] | None:
    """Find entry at nearest Fibonacci retracement level."""
    candidates: list[tuple[float, str]] = []
    for p in fib_patterns:
        level_price = _extract_price_from_description(p.description)
        if level_price is None:
            continue

        if (direction == Direction.LONG and level_price < current_price) or (
            direction == Direction.SHORT and level_price > current_price
        ):
            candidates.append((level_price, p.description))

    if not candidates:
        return None

    if direction == Direction.LONG:
        best_price, _ = max(candidates, key=lambda x: x[0])
    else:
        best_price, _ = min(candidates, key=lambda x: x[0])

    return {
        "type": "conservative_fib",
        "price": best_price,
        "condition": f"Wejscie przy poziomie Fibonacci {best_price:.5f}",
    }


def _extract_price_from_description(description: str) -> float | None:
    """Extract a numeric price from a pattern description string.

    Looks for patterns like "at 1.12345" or "Level 1.12345".
    """
    match = _PRICE_RE.search(description)
    if match:
        return float(match.group(1))
    return None
