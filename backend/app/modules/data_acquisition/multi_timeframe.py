import asyncio
import logging
from dataclasses import dataclass

from app.core.models import OHLCVData
from app.modules.data_acquisition.fallback_chain import FallbackChainManager
from app.modules.data_acquisition.ohlcv_cache import OHLCVCacheService, get_cached_ohlcv
from app.modules.data_acquisition.timeframes import AnalysisTimeframePlan, DataTimeframe

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MultiTimeframeFetchBundle:
    main_timeframe: DataTimeframe
    candles_by_timeframe: dict[DataTimeframe, list[OHLCVData]]
    errors: dict[DataTimeframe, str]

    def get(self, timeframe: DataTimeframe) -> list[OHLCVData]:
        return self.candles_by_timeframe.get(timeframe, [])

    @property
    def main_ohlcv(self) -> list[OHLCVData]:
        return self.get(self.main_timeframe)


class MultiTimeframeFetcher:
    def __init__(self, chain: FallbackChainManager, session_factory) -> None:
        self._chain = chain
        self._session_factory = session_factory

    async def fetch(
        self,
        symbol: str,
        plan: AnalysisTimeframePlan,
        period: str = "200d",
    ) -> MultiTimeframeFetchBundle:
        tasks = {
            timeframe: asyncio.create_task(self._fetch_single_timeframe(symbol, timeframe, period))
            for timeframe in plan.required_timeframes
        }

        candles_by_timeframe: dict[DataTimeframe, list[OHLCVData]] = {}
        errors: dict[DataTimeframe, str] = {}

        for timeframe in plan.required_timeframes:
            task = tasks[timeframe]
            try:
                candles_by_timeframe[timeframe] = await task
            except Exception as exc:
                if timeframe == plan.main_timeframe:
                    raise

                logger.warning("Auxiliary timeframe fetch failed for %s/%s: %s", symbol, timeframe, exc)
                candles_by_timeframe[timeframe] = []
                errors[timeframe] = str(exc)

        return MultiTimeframeFetchBundle(
            main_timeframe=plan.main_timeframe,
            candles_by_timeframe=candles_by_timeframe,
            errors=errors,
        )

    async def _fetch_single_timeframe(
        self,
        symbol: str,
        timeframe: DataTimeframe,
        period: str,
    ) -> list[OHLCVData]:
        try:
            async with self._session_factory() as session:
                cache_service = OHLCVCacheService(session)

                async def _fetch(fetch_symbol: str, timeframe_value: str, fetch_period: str) -> list[OHLCVData]:
                    return await self._chain.fetch_ohlcv(fetch_symbol, DataTimeframe(timeframe_value), fetch_period)

                candles = await cache_service.get_ohlcv(symbol, timeframe.value, period, _fetch)
                if candles:
                    return candles
        except Exception as exc:
            logger.warning(
                "OHLCVCacheService failed for %s/%s, falling back to direct fetch: %s",
                symbol,
                timeframe,
                exc,
            )

        try:
            return await self._chain.fetch_ohlcv(symbol, timeframe, period)
        except Exception as exc:
            try:
                async with self._session_factory() as session:
                    cached = await get_cached_ohlcv(session, symbol, timeframe.value)
                if cached:
                    logger.info("Using %d cached candles for %s/%s", len(cached), symbol, timeframe)
                    return cached
            except Exception as cache_exc:
                logger.warning("OHLCV cache read also failed for %s/%s: %s", symbol, timeframe, cache_exc)

            raise exc
