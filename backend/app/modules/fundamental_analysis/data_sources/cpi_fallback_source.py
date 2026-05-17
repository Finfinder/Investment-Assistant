"""Staleness-aware fallback source dla CPI US/CA/CH."""

import logging

from .bfs_cpi_source import BfsCpiSource
from .bls_cpi_source import BlsCpiSource
from .cpi_yoy import CPI_MAX_AGE_DAYS, is_observation_fresh
from .fred_source import FredSource
from .macro_observation import MacroObservation
from .statcan_cpi_source import StatCanCpiSource

logger = logging.getLogger(__name__)


class CpiFallbackSource:
    """Uses FRED as primary and country APIs as fallback for stale CPI data."""

    def __init__(
        self,
        fred: FredSource,
        bls: BlsCpiSource | None = None,
        statcan: StatCanCpiSource | None = None,
        bfs: BfsCpiSource | None = None,
    ) -> None:
        self._fred = fred
        self._bls = bls or BlsCpiSource()
        self._statcan = statcan or StatCanCpiSource()
        self._bfs = bfs or BfsCpiSource()

    async def _fetch_country_observation(self, indicator_name: str) -> MacroObservation | None:
        if indicator_name == "cpi_us":
            return await self._bls.fetch_us_cpi_yoy()
        if indicator_name == "cpi_ca":
            return await self._statcan.fetch_ca_cpi_yoy()
        if indicator_name == "cpi_ch":
            return await self._bfs.fetch_ch_cpi_yoy()
        return None

    async def fetch_indicator(self, indicator_name: str, lookback_days: int = 365) -> float | None:
        if indicator_name not in {"cpi_us", "cpi_ca", "cpi_ch"}:
            logger.warning("CPI fallback: unsupported indicator %s", indicator_name)
            return None

        fred_observation = await self._fred.fetch_indicator_observation(indicator_name, lookback_days)
        if fred_observation is not None and is_observation_fresh(fred_observation, max_age_days=CPI_MAX_AGE_DAYS):
            logger.info("CPI fallback: using FRED for %s (%s)", indicator_name, fred_observation.period)
            return fred_observation.value

        if fred_observation is None:
            logger.warning("CPI fallback: FRED missing %s, trying country source", indicator_name)
        else:
            logger.warning(
                "CPI fallback: FRED stale %s (%s), trying country source",
                indicator_name,
                fred_observation.period,
            )

        country_observation = await self._fetch_country_observation(indicator_name)
        if country_observation is not None and is_observation_fresh(country_observation, max_age_days=CPI_MAX_AGE_DAYS):
            logger.info(
                "CPI fallback: using %s for %s (%s)",
                country_observation.source,
                indicator_name,
                country_observation.period,
            )
            return country_observation.value

        if country_observation is not None:
            logger.warning(
                "CPI fallback: country source stale %s (%s)",
                indicator_name,
                country_observation.period,
            )

        return None

    async def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]:
        results: dict[str, float | None] = {}
        for name in indicator_names:
            results[name] = await self.fetch_indicator(name)
        return results
