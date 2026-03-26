"""REST API endpoints for pattern recognition."""

import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.v1.market_data import get_fallback_chain
from app.core.models import PatternDetection, Timeframe
from app.modules.data_acquisition.fallback_chain import DataProviderError
from app.modules.pattern_recognition.candlestick import detect_candlestick_patterns
from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
from app.modules.pattern_recognition.fibonacci import calculate_fibonacci_levels
from app.modules.pattern_recognition.iki_detector import detect_iki_pattern
from app.modules.pattern_recognition.support_resistance import detect_support_resistance

logger = logging.getLogger(__name__)

router = APIRouter(tags=["patterns"])

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9]{2,20}$")


class PatternsRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    period: str = "180d"


class PatternsResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    patterns: list[PatternDetection]


@router.post("/patterns", response_model=PatternsResponse)
async def detect_patterns(body: PatternsRequest) -> PatternsResponse:
    if not SYMBOL_PATTERN.match(body.symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")

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

    return PatternsResponse(
        symbol=body.symbol.upper(),
        timeframe=body.timeframe,
        patterns=patterns,
    )
