"""REST API endpoints for pattern recognition."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.market_data import get_fallback_chain
from app.api.v1.validators import validate_period, validate_symbol
from app.core.auth import require_auth
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
    warnings: list[str] = Field(default_factory=list)


@router.post("/patterns", response_model=PatternsResponse)
@limiter.limit("20/minute")
async def detect_patterns(
    request: Request, body: PatternsRequest, user: str = Depends(require_auth)
) -> PatternsResponse:
    validate_symbol(body.symbol)
    validate_period(body.period)

    chain = get_fallback_chain()
    try:
        ohlcv = await chain.fetch_ohlcv(body.symbol, body.timeframe, body.period)
    except DataProviderError as exc:
        logger.exception("All providers failed for %s: %s", body.symbol, exc)
        raise HTTPException(status_code=502, detail="Unable to fetch market data from any provider") from exc

    if not ohlcv:
        raise HTTPException(status_code=404, detail="No data returned for the given symbol")

    patterns: list[PatternDetection] = []
    warnings: list[str] = []

    # Lista detektorów do wywołania — każdy opakowany w try/except
    # aby izolować awarie i zwracać częściowe wyniki
    detectors = [
        ("candlestick", detect_candlestick_patterns),
        ("support_resistance", detect_support_resistance),
        ("fibonacci", calculate_fibonacci_levels),
        ("iki", detect_iki_pattern),
        ("chart_patterns", detect_chart_patterns),
    ]
    for detector_name, detector_fn in detectors:
        try:
            patterns.extend(detector_fn(ohlcv))
        except Exception as exc:
            logger.exception("Detector '%s' failed for %s: %s", detector_name, body.symbol, exc)
            warnings.append(f"{detector_name}: {type(exc).__name__}")

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
        warnings=warnings,
    )
