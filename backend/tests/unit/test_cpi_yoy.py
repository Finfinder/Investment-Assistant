"""Tests for CPI YoY helper utilities."""

from datetime import date

import pytest

from app.modules.fundamental_analysis.data_sources.cpi_yoy import (
    CPI_MAX_AGE_DAYS,
    compute_yoy_observation,
    is_observation_fresh,
    is_valid_cpi_value,
    parse_bls_period,
    parse_monthly_period,
)
from app.modules.fundamental_analysis.data_sources.macro_observation import MacroObservation


def test_parse_monthly_period_supports_multiple_formats():
    assert parse_monthly_period("2025-04") == date(2025, 4, 1)
    assert parse_monthly_period("2025-04-15") == date(2025, 4, 1)
    assert parse_monthly_period("202504") == date(2025, 4, 1)


def test_parse_monthly_period_rejects_invalid_values():
    assert parse_monthly_period("2025-13") is None
    assert parse_monthly_period("bad") is None


def test_parse_bls_period_accepts_monthly_codes_only():
    assert parse_bls_period("2025", "M04") == date(2025, 4, 1)
    assert parse_bls_period("2025", "M13") is None


def test_is_valid_cpi_value_rejects_non_finite_or_zero():
    assert is_valid_cpi_value(1.0)
    assert not is_valid_cpi_value(0.0)
    assert not is_valid_cpi_value(float("inf"))
    assert not is_valid_cpi_value(float("nan"))


def test_compute_yoy_observation_uses_latest_month_with_previous_year_pair():
    observation = compute_yoy_observation(
        {
            date(2024, 3, 1): 100.0,
            date(2025, 3, 1): 103.0,
            date(2025, 2, 1): 102.0,
        },
        source="test",
    )

    assert observation is not None
    assert observation.value == pytest.approx(3.0)
    assert observation.period == date(2025, 3, 1)
    assert observation.source == "test"


def test_compute_yoy_observation_returns_none_without_previous_year_pair():
    observation = compute_yoy_observation(
        {
            date(2025, 3, 1): 103.0,
            date(2025, 2, 1): 102.0,
        },
        source="test",
    )

    assert observation is None


def test_compute_yoy_observation_uses_latest_available_pair_when_max_period_has_no_pair():
    observation = compute_yoy_observation(
        {
            date(2024, 2, 1): 100.0,
            date(2025, 2, 1): 103.0,
            date(2025, 3, 1): 104.0,
        },
        source="test",
    )

    assert observation is not None
    assert observation.period == date(2025, 2, 1)
    assert observation.value == pytest.approx(3.0)


def test_is_observation_fresh_honors_max_age_boundary():
    reference_today = date(2026, 5, 16)
    fresh_observation = MacroObservation(value=2.0, period=date(2026, 3, 1), source="x")
    stale_observation = MacroObservation(value=2.0, period=date(2025, 12, 1), source="x")

    assert is_observation_fresh(fresh_observation, today=reference_today, max_age_days=CPI_MAX_AGE_DAYS)
    assert not is_observation_fresh(stale_observation, today=reference_today, max_age_days=CPI_MAX_AGE_DAYS)
