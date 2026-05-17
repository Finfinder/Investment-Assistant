"""Helpery do obliczania i walidacji CPI YoY."""

import calendar
import math
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime

from .macro_observation import MacroObservation

CPI_MAX_AGE_DAYS = 90
_MONTH_PERIOD_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_DATE_PERIOD_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])-([0-2]\d|3[0-1])$")
_COMPACT_PERIOD_RE = re.compile(r"^(\d{4})(0[1-9]|1[0-2])$")
_BLS_PERIOD_RE = re.compile(r"^M(0[1-9]|1[0-2])$")


def is_valid_cpi_value(value: float) -> bool:
    """Sprawdza czy wartosc CPI moze byc uzyta do obliczen."""
    return math.isfinite(value) and not math.isclose(value, 0.0, abs_tol=1e-12)


def parse_monthly_period(period: str) -> date | None:
    """Parsuje okresy miesieczne: YYYY-MM, YYYY-MM-DD, YYYYMM."""
    text = period.strip()

    month_match = _MONTH_PERIOD_RE.match(text)
    if month_match:
        year = int(month_match.group(1))
        month = int(month_match.group(2))
        return date(year, month, 1)

    compact_match = _COMPACT_PERIOD_RE.match(text)
    if compact_match:
        year = int(compact_match.group(1))
        month = int(compact_match.group(2))
        return date(year, month, 1)

    date_match = _DATE_PERIOD_RE.match(text)
    if date_match:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().replace(day=1)
        except ValueError:
            return None

    return None


def parse_bls_period(year: str, period: str) -> date | None:
    """Parsuje okres BLS (year + M01..M12) do daty miesiaca."""
    if _BLS_PERIOD_RE.match(period.strip()) is None:
        return None

    try:
        parsed_year = int(year)
        parsed_month = int(period[1:])
    except ValueError:
        return None

    return date(parsed_year, parsed_month, 1)


def compute_yoy_observation(index_values: Mapping[date, float], source: str) -> MacroObservation | None:
    """Liczy CPI YoY z indeksu miesiecznego i zwraca obserwacje YoY."""
    if not index_values:
        return None

    filtered = {period: value for period, value in index_values.items() if is_valid_cpi_value(value)}
    if not filtered:
        return None

    for latest_period in sorted(filtered, reverse=True):
        previous_year_period = date(latest_period.year - 1, latest_period.month, 1)
        previous_value = filtered.get(previous_year_period)
        current_value = filtered.get(latest_period)

        if previous_value is None or current_value is None:
            continue

        yoy = ((current_value / previous_value) - 1.0) * 100.0
        if not math.isfinite(yoy):
            continue

        return MacroObservation(
            value=yoy,
            period=latest_period,
            source=source,
            unit="pct_yoy",
        )

    return None


def is_observation_fresh(
    observation: MacroObservation,
    *,
    max_age_days: int = CPI_MAX_AGE_DAYS,
    today: date | None = None,
) -> bool:
    """Weryfikuje czy obserwacja miesci sie w progu swiezosci."""
    reference_day = today or datetime.now(UTC).date()
    end_of_period = date(
        observation.period.year,
        observation.period.month,
        calendar.monthrange(observation.period.year, observation.period.month)[1],
    )
    age_days = (reference_day - end_of_period).days
    return age_days <= max_age_days
