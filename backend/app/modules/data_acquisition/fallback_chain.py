import logging
import time

from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.interfaces import DataProvider

logger = logging.getLogger(__name__)


class DataProviderError(Exception):
    """Raised when all providers in the chain fail."""


class FallbackChainManager:
    """Iterates through providers by priority, returns data from the first working one."""

    def __init__(self, providers: list[DataProvider]) -> None:
        self._providers = sorted(providers, key=lambda p: p.priority.value)

    @property
    def providers(self) -> list[DataProvider]:
        return list(self._providers)

    async def fetch_ohlcv(self, symbol: str, timeframe: Timeframe, period: str) -> list[OHLCVData]:
        errors: list[str] = []

        for provider in self._providers:
            start = time.monotonic()
            try:
                result = await provider.fetch_ohlcv(symbol, timeframe, period)
                elapsed = time.monotonic() - start

                if result:
                    logger.info(
                        "Provider %s responded for %s in %.2fs (%d candles)",
                        provider.name,
                        symbol,
                        elapsed,
                        len(result),
                    )
                    return result

                logger.warning(
                    "Provider %s returned empty data for %s (%.2fs), trying next",
                    provider.name,
                    symbol,
                    elapsed,
                )
                errors.append(f"{provider.name}: empty response")

            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.warning(
                    "Provider %s failed for %s after %.2fs: %s — falling back",
                    provider.name,
                    symbol,
                    elapsed,
                    exc,
                )
                errors.append(f"{provider.name}: {exc}")

        raise DataProviderError(f"All providers failed for {symbol}/{timeframe}/{period}: " + "; ".join(errors))


def build_fallback_chain() -> FallbackChainManager:
    """Build a FallbackChainManager from configured API keys.

    Provider priority: YFinance (primary) -> TwelveData (secondary) -> FMP (tertiary).
    """
    from app.core.config import get_settings
    from app.modules.data_acquisition.providers.yfinance_provider import YFinanceProvider

    settings = get_settings()
    providers: list[DataProvider] = [YFinanceProvider()]

    if settings.TWELVE_DATA_API_KEY:
        from app.modules.data_acquisition.providers.twelve_data_provider import TwelveDataProvider

        providers.append(TwelveDataProvider(api_key=settings.TWELVE_DATA_API_KEY))

    if settings.FMP_API_KEY:
        from app.modules.data_acquisition.providers.fmp_provider import FMPProvider

        providers.append(FMPProvider(api_key=settings.FMP_API_KEY))

    return FallbackChainManager(providers)
