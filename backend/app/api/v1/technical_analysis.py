import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.market_data import get_fallback_chain
from app.api.v1.validators import validate_period, validate_symbol
from app.core.models import IndicatorValue, MovingAverage, PivotPoints, SignalSummary, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.fallback_chain import DataProviderError
from app.modules.technical_analysis.indicators import calculate_indicators
from app.modules.technical_analysis.moving_averages import calculate_moving_averages
from app.modules.technical_analysis.pivot_points import calculate_pivot_points
from app.modules.technical_analysis.summary import calculate_summaries

logger = logging.getLogger(__name__)

router = APIRouter(tags=["technical-analysis"])


class TechnicalAnalysisRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    period: str = "90d"


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    indicators: list[IndicatorValue]
    moving_averages: list[MovingAverage]
    pivot_points: list[PivotPoints]
    summary: SignalSummary


@router.post("/technical-analysis", response_model=TechnicalAnalysisResponse)
@limiter.limit("20/minute")
async def run_technical_analysis(request: Request, body: TechnicalAnalysisRequest) -> TechnicalAnalysisResponse:
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

    indicators = calculate_indicators(ohlcv)
    moving_avgs = calculate_moving_averages(ohlcv)

    last = ohlcv[-1]
    pivots = calculate_pivot_points(last.high, last.low, last.close, last.open)

    summary = calculate_summaries(indicators, moving_avgs)

    return TechnicalAnalysisResponse(
        symbol=body.symbol.upper(),
        timeframe=body.timeframe,
        indicators=indicators,
        moving_averages=moving_avgs,
        pivot_points=pivots,
        summary=summary,
    )
