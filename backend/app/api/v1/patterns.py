"""REST API endpoints for pattern recognition."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.market_data import get_fallback_chain
from app.api.v1.validators import validate_period, validate_symbol
from app.core.models import PatternDetection, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.fallback_chain import DataProviderError
from app.modules.pattern_recognition.candlestick import detect_candlestick_patterns
from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
from app.modules.pattern_recognition.fibonacci import calculate_fibonacci_levels
from app.modules.pattern_recognition.iki_detector import detect_iki_pattern
from app.modules.pattern_recognition.relevance_scorer import calculate_target_prices, score_patterns
from app.modules.pattern_recognition.support_resistance import detect_support_resistance

logger = logging.getLogger(__name__)

router = APIRouter(tags=["patterns"])


class PatternsRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    period: str = "180d"


class PatternsResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    patterns: list[PatternDetection]


@router.post("/patterns", response_model=PatternsResponse)
@limiter.limit("20/minute")
async def detect_patterns(request: Request, body: PatternsRequest) -> PatternsResponse:
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

    patterns: list[PatternDetection] = []
    patterns.extend(detect_candlestick_patterns(ohlcv))
    patterns.extend(detect_support_resistance(ohlcv))
    patterns.extend(calculate_fibonacci_levels(ohlcv))
    patterns.extend(detect_iki_pattern(ohlcv))
    patterns.extend(detect_chart_patterns(ohlcv))

    # Wypełnij detected_at_timestamp z danych OHLCV
    for pattern in patterns:
        idx = pattern.detected_at_index if pattern.detected_at_index is not None else len(ohlcv) - 1
        idx = max(0, min(idx, len(ohlcv) - 1))
        pattern.detected_at_timestamp = ohlcv[idx].timestamp.isoformat()

    calculate_target_prices(patterns, ohlcv)
    current_price = float(ohlcv[-1].close)
    try:
        score_patterns(patterns, len(ohlcv), current_price)
    except Exception as exc:
        logger.warning("score_patterns failed: %s", exc)
    patterns.sort(key=lambda p: p.relevance_score, reverse=True)

    return PatternsResponse(
        symbol=body.symbol.upper(),
        timeframe=body.timeframe,
        patterns=patterns,
    )
