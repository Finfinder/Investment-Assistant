import logging
from enum import StrEnum
from typing import Protocol, runtime_checkable

from app.core.models import OHLCVData, Timeframe

logger = logging.getLogger(__name__)


class DataProviderPriority(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    FALLBACK = "fallback"


@runtime_checkable
class DataProvider(Protocol):
    """Contract for all market data providers."""

    @property
    def name(self) -> str: ...

    @property
    def priority(self) -> DataProviderPriority: ...

    async def fetch_ohlcv(
        self, symbol: str, timeframe: Timeframe, period: str
    ) -> list[OHLCVData]: ...

    def get_supported_symbols(self) -> list[str]: ...

    async def is_available(self) -> bool: ...
