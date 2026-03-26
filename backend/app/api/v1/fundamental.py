"""REST API endpoint for fundamental analysis."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.instrument_classifier import classify_instrument
from app.core.models import FundamentalData, InstrumentType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fundamental-analysis"])


class FundamentalRequest(BaseModel):
    symbol: str


@router.post("/fundamental-analysis", response_model=FundamentalData)
async def analyze_fundamental(request: FundamentalRequest) -> FundamentalData:
    """Run fundamental analysis for a given instrument.

    Automatically routes to the correct analyzer based on instrument type
    (Forex, Commodity, or Index).
    """
    instrument_type = classify_instrument(request.symbol)
    if instrument_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Nierozpoznany instrument: {request.symbol}. "
            "Podaj symbol forex (np. EURUSD), surowca (np. GOLD) lub indeksu (np. US500).",
        )

    try:
        if instrument_type == InstrumentType.FOREX:
            from app.modules.fundamental_analysis.forex import analyze_forex

            return await analyze_forex(request.symbol)

        if instrument_type == InstrumentType.COMMODITY:
            from app.modules.fundamental_analysis.commodities import analyze_commodity

            return await analyze_commodity(request.symbol)

        # INDEX
        from app.modules.fundamental_analysis.indices import analyze_index

        return await analyze_index(request.symbol)

    except Exception:
        logger.exception("Fundamental analysis failed for %s", request.symbol)
        raise HTTPException(
            status_code=500,
            detail=f"Blad analizy fundamentalnej dla {request.symbol}.",
        ) from None
