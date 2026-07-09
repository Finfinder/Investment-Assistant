"""REST API endpoint for fundamental analysis."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.validators import validate_symbol
from app.core.auth import require_auth
from app.core.instrument_classifier import classify_instrument
from app.core.models import FundamentalData, InstrumentType
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fundamental-analysis"])


class FundamentalRequest(BaseModel):
    symbol: str


@router.post("/fundamental-analysis", response_model=FundamentalData)
@limiter.limit("20/minute")
async def analyze_fundamental(
    request: Request, body: FundamentalRequest, user: str = Depends(require_auth)
) -> FundamentalData:
    """Run fundamental analysis for a given instrument.

    Automatically routes to the correct analyzer based on instrument type
    (Forex, Commodity, or Index).
    """
    validate_symbol(body.symbol)
    instrument_type = classify_instrument(body.symbol)
    if instrument_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Nierozpoznany instrument: {body.symbol}. "
            "Podaj symbol forex (np. EURUSD), surowca (np. GOLD) lub indeksu (np. US500).",
        )

    try:
        if instrument_type == InstrumentType.FOREX:
            from app.modules.fundamental_analysis.forex import analyze_forex

            return await analyze_forex(body.symbol)

        if instrument_type == InstrumentType.COMMODITY:
            from app.modules.fundamental_analysis.commodities import analyze_commodity

            return await analyze_commodity(body.symbol)

        # INDEX
        from app.modules.fundamental_analysis.indices import analyze_index

        return await analyze_index(body.symbol)

    except Exception:
        # The global exception handler logs the full chain (with correlation ID)
        # and returns a sanitized response. Re-raise to let it take over.
        raise
