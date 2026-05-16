"""Macro data facade for combining OECD and FRED sources."""

from typing import Protocol, runtime_checkable

from .fred_source import FredSource
from .oecd_sdmx_source import OecdSdmxSource


@runtime_checkable
class MacroIndicatorSource(Protocol):
    """Minimal macro indicator contract used by analyzers."""

    async def fetch_indicator(self, indicator_name: str, lookback_days: int = 365) -> float | None: ...

    async def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]: ...


class MacroDataSource:
    """Routes JP CPI to OECD and all other indicators to FRED."""

    def __init__(self, fred: FredSource | None = None, oecd: OecdSdmxSource | None = None) -> None:
        self._fred = fred or FredSource()
        self._oecd = oecd or OecdSdmxSource()

    async def fetch_indicator(self, indicator_name: str, lookback_days: int = 365) -> float | None:
        if indicator_name == "cpi_jp":
            return await self._oecd.fetch_jp_cpi_yoy()
        return await self._fred.fetch_indicator(indicator_name, lookback_days)

    async def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]:
        results: dict[str, float | None] = {}
        for name in indicator_names:
            results[name] = await self.fetch_indicator(name)
        return results
