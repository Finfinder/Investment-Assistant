from app.core.models import OHLCVData, PivotPoints, PivotType


def get_pivot_candle(daily_ohlcv: list[OHLCVData]) -> OHLCVData | None:
    """Select the proper daily candle for Pivot Points calculation.

    Returns the previous completed day (second-to-last candle) when available,
    the only candle when just one exists, or None for an empty list.
    """
    if not daily_ohlcv:
        return None
    if len(daily_ohlcv) >= 2:
        return daily_ohlcv[-2]
    return daily_ohlcv[-1]


def calculate_pivot_points(high: float, low: float, close: float, open_: float) -> list[PivotPoints]:
    """Calculate 5 types of pivot points from a single OHLC candle.

    Returns: Classic, Fibonacci, Camarilla, Woodie, DeMark.
    """
    return [
        _classic(high, low, close),
        _fibonacci(high, low, close),
        _camarilla(high, low, close),
        _woodie(high, low, close),
        _demark(high, low, close, open_),
    ]


def _classic(h: float, lo: float, c: float) -> PivotPoints:
    pp = (h + lo + c) / 3
    return PivotPoints(
        type=PivotType.CLASSIC,
        pp=round(pp, 5),
        r1=round(2 * pp - lo, 5),
        s1=round(2 * pp - h, 5),
        r2=round(pp + (h - lo), 5),
        s2=round(pp - (h - lo), 5),
        r3=round(h + 2 * (pp - lo), 5),
        s3=round(lo - 2 * (h - pp), 5),
    )


def _fibonacci(h: float, lo: float, c: float) -> PivotPoints:
    pp = (h + lo + c) / 3
    diff = h - lo
    return PivotPoints(
        type=PivotType.FIBONACCI,
        pp=round(pp, 5),
        r1=round(pp + 0.382 * diff, 5),
        s1=round(pp - 0.382 * diff, 5),
        r2=round(pp + 0.618 * diff, 5),
        s2=round(pp - 0.618 * diff, 5),
        r3=round(pp + diff, 5),
        s3=round(pp - diff, 5),
    )


def _camarilla(h: float, lo: float, c: float) -> PivotPoints:
    pp = (h + lo + c) / 3
    diff = h - lo
    return PivotPoints(
        type=PivotType.CAMARILLA,
        pp=round(pp, 5),
        r1=round(c + 1.1 * diff / 12, 5),
        s1=round(c - 1.1 * diff / 12, 5),
        r2=round(c + 1.1 * diff / 6, 5),
        s2=round(c - 1.1 * diff / 6, 5),
        r3=round(c + 1.1 * diff / 4, 5),
        s3=round(c - 1.1 * diff / 4, 5),
    )


def _woodie(h: float, lo: float, c: float) -> PivotPoints:
    pp = (h + lo + 2 * c) / 4
    return PivotPoints(
        type=PivotType.WOODIE,
        pp=round(pp, 5),
        r1=round(2 * pp - lo, 5),
        s1=round(2 * pp - h, 5),
        r2=round(pp + (h - lo), 5),
        s2=round(pp - (h - lo), 5),
        r3=round(h + 2 * (pp - lo), 5),
        s3=round(lo - 2 * (h - pp), 5),
    )


def _demark(h: float, lo: float, c: float, o: float) -> PivotPoints:
    if c < o:
        x = h + 2 * lo + c
    elif c > o:
        x = 2 * h + lo + c
    else:
        x = h + lo + 2 * c
    pp = x / 4
    return PivotPoints(
        type=PivotType.DEMARK,
        pp=round(pp, 5),
        r1=round(x / 2 - lo, 5),
        s1=round(x / 2 - h, 5),
    )
