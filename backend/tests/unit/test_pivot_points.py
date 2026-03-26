import pytest

from app.core.models import PivotType
from app.modules.technical_analysis.pivot_points import calculate_pivot_points

# Test data: H=110, L=90, C=105, OP=100
H, L, C, OP = 110.0, 90.0, 105.0, 100.0


def test_classic():
    results = calculate_pivot_points(H, L, C, OP)
    classic = next(r for r in results if r.type == PivotType.CLASSIC)
    pp = (H + L + C) / 3  # 101.6667
    assert classic.pp == pytest.approx(pp, abs=1e-4)
    assert classic.r1 == pytest.approx(2 * pp - L, abs=1e-4)
    assert classic.s1 == pytest.approx(2 * pp - H, abs=1e-4)
    assert classic.r2 == pytest.approx(pp + (H - L), abs=1e-4)
    assert classic.s2 == pytest.approx(pp - (H - L), abs=1e-4)
    assert classic.r3 == pytest.approx(H + 2 * (pp - L), abs=1e-4)
    assert classic.s3 == pytest.approx(L - 2 * (H - pp), abs=1e-4)


def test_fibonacci():
    results = calculate_pivot_points(H, L, C, OP)
    fib = next(r for r in results if r.type == PivotType.FIBONACCI)
    pp = (H + L + C) / 3
    diff = H - L  # 20
    assert fib.pp == pytest.approx(pp, abs=1e-4)
    assert fib.r1 == pytest.approx(pp + 0.382 * diff, abs=1e-4)
    assert fib.s1 == pytest.approx(pp - 0.382 * diff, abs=1e-4)
    assert fib.r2 == pytest.approx(pp + 0.618 * diff, abs=1e-4)
    assert fib.s2 == pytest.approx(pp - 0.618 * diff, abs=1e-4)


def test_camarilla():
    results = calculate_pivot_points(H, L, C, OP)
    cam = next(r for r in results if r.type == PivotType.CAMARILLA)
    diff = H - L
    assert cam.r1 == pytest.approx(C + 1.1 * diff / 12, abs=1e-4)
    assert cam.s1 == pytest.approx(C - 1.1 * diff / 12, abs=1e-4)
    assert cam.r3 == pytest.approx(C + 1.1 * diff / 4, abs=1e-4)
    assert cam.s3 == pytest.approx(C - 1.1 * diff / 4, abs=1e-4)


def test_woodie():
    results = calculate_pivot_points(H, L, C, OP)
    woodie = next(r for r in results if r.type == PivotType.WOODIE)
    pp = (H + L + 2 * C) / 4  # 102.5
    assert woodie.pp == pytest.approx(pp, abs=1e-4)
    assert woodie.r1 == pytest.approx(2 * pp - L, abs=1e-4)
    assert woodie.s1 == pytest.approx(2 * pp - H, abs=1e-4)


def test_demark_close_greater_than_open():
    """Close > Open: X = 2*H + L + C"""
    results = calculate_pivot_points(H, L, C, OP)
    dm = next(r for r in results if r.type == PivotType.DEMARK)
    x = 2 * H + L + C  # 315
    assert dm.pp == pytest.approx(x / 4, abs=1e-4)
    assert dm.r1 == pytest.approx(x / 2 - L, abs=1e-4)
    assert dm.s1 == pytest.approx(x / 2 - H, abs=1e-4)
    # DeMark has no S2/S3/R2/R3
    assert dm.s2 is None
    assert dm.r2 is None


def test_demark_close_less_than_open():
    """Close < Open: X = H + 2*L + C"""
    results = calculate_pivot_points(H, L, close=95.0, open_=100.0)
    dm = next(r for r in results if r.type == PivotType.DEMARK)
    x = H + 2 * L + 95.0  # 285
    assert dm.pp == pytest.approx(x / 4, abs=1e-4)


def test_demark_close_equal_open():
    """Close == Open: X = H + L + 2*C"""
    results = calculate_pivot_points(H, L, close=100.0, open_=100.0)
    dm = next(r for r in results if r.type == PivotType.DEMARK)
    x = H + L + 2 * 100.0  # 400
    assert dm.pp == pytest.approx(x / 4, abs=1e-4)


def test_returns_5_types():
    results = calculate_pivot_points(H, L, C, OP)
    assert len(results) == 5
    types = {r.type for r in results}
    assert types == {PivotType.CLASSIC, PivotType.FIBONACCI, PivotType.CAMARILLA, PivotType.WOODIE, PivotType.DEMARK}
