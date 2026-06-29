import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.market_data import get_fallback_chain
from app.api.v1.validators import validate_period, validate_symbol
from app.core.auth import require_auth
from app.core.models import IndicatorPreset, IndicatorValue, MovingAverage, PivotPoints, SignalSummary, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.fallback_chain import DataProviderError
from app.modules.technical_analysis.indicators import calculate_indicators
from app.modules.technical_analysis.moving_averages import calculate_moving_averages
from app.modules.technical_analysis.pivot_points import calculate_pivot_points, get_pivot_candle
from app.modules.technical_analysis.presets import get_preset_params
from app.modules.technical_analysis.summary import calculate_summaries

logger = logging.getLogger(__name__)

router = APIRouter(tags=["technical-analysis"])


class TechnicalAnalysisRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    period: str = "90d"
    preset: IndicatorPreset = IndicatorPreset.INVESTING


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    indicators: list[IndicatorValue]
    moving_averages: list[MovingAverage]
    pivot_points: list[PivotPoints]
    summary: SignalSummary


@router.post("/technical-analysis", response_model=TechnicalAnalysisResponse)
@limiter.limit("20/minute")
async def run_technical_analysis(
    request: Request, body: TechnicalAnalysisRequest, user: str = Depends(require_auth)
) -> TechnicalAnalysisResponse:
    validate_symbol(body.symbol)
    validate_period(body.period)

    chain = get_fallback_chain()
    try:
        ohlcv = await chain.fetch_ohlcv(body.symbol, body.timeframe, body.period)
    except DataProviderError as exc:
        logger.error("All providers failed for %s: %s", body.symbol, exc)
        raise HTTPException(status_code=502, detail="Unable to fetch market data from any provider") from exc

    if not ohlcv:
        raise HTTPException(status_code=404, detail="No data returned for the given symbol")

    params = get_preset_params(body.preset)
    indicators = calculate_indicators(ohlcv, params)
    moving_avgs = calculate_moving_averages(ohlcv)

    # Fetch D1 candle for Pivot Points
    pivot_candle = None
    if body.timeframe == Timeframe.D1:
        pivot_candle = get_pivot_candle(ohlcv)
    else:
        try:
            daily = await chain.fetch_ohlcv(body.symbol, Timeframe.D1, "5d")
            pivot_candle = get_pivot_candle(daily)
        except Exception as exc:
            logger.warning("D1 candle fetch for pivot points failed: %s", exc)

    candle = pivot_candle or ohlcv[-1]
    pivots = calculate_pivot_points(candle.high, candle.low, candle.close, candle.open)

    summary = calculate_summaries(indicators, moving_avgs)

    return TechnicalAnalysisResponse(
        symbol=body.symbol.upper(),
        timeframe=body.timeframe,
        indicators=indicators,
        moving_averages=moving_avgs,
        pivot_points=pivots,
        summary=summary,
    )
