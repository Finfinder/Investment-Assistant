"""REST API endpoint for fundamental analysis."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.models import FundamentalData, InstrumentType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fundamental-analysis"])

# Classify symbols into instrument types
FOREX_PAIRS: set[str] = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
    "EURGBP", "EURJPY", "GBPJPY", "NZDUSD", "AUDCAD", "AUDCHF",
    "AUDJPY", "CADJPY", "CHFJPY", "EURCHF", "EURAUD", "EURCAD",
    "GBPCAD", "GBPCHF",
}

COMMODITY_SYMBOLS: set[str] = {
    "GOLD", "XAUUSD", "SILVER", "XAGUSD", "OIL", "WTIUSD",
    "BRENT", "NATGAS", "COPPER", "PLATINUM", "PALLADIUM",
}

INDEX_SYMBOLS: set[str] = {
    "US500", "US30", "US100", "SPX", "NDX", "DJI",
    "DE40", "DAX", "EU50", "UK100", "FTSE",
    "JP225", "NIKKEI", "AU200", "CA60",
}


def _classify_instrument(symbol: str) -> InstrumentType:
    """Auto-detect instrument type from symbol."""
    clean = symbol.upper().replace("/", "").replace("-", "")
    if clean in FOREX_PAIRS:
        return InstrumentType.FOREX
    if clean in COMMODITY_SYMBOLS:
        return InstrumentType.COMMODITY
    if clean in INDEX_SYMBOLS:
        return InstrumentType.INDEX
    # Heuristic: 6-char alphanumeric without digits is likely forex
    if len(clean) == 6 and clean.isalpha():
        return InstrumentType.FOREX
    raise ValueError(f"Cannot classify instrument: {symbol}")


class FundamentalRequest(BaseModel):
    symbol: str


@router.post("/fundamental-analysis", response_model=FundamentalData)
async def analyze_fundamental(request: FundamentalRequest) -> FundamentalData:
    """Run fundamental analysis for a given instrument.

    Automatically routes to the correct analyzer based on instrument type
    (Forex, Commodity, or Index).
    """
    try:
        instrument_type = _classify_instrument(request.symbol)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Nierozpoznany instrument: {request.symbol}. "
            "Podaj symbol forex (np. EURUSD), surowca (np. GOLD) lub indeksu (np. US500).",
        ) from None

    try:
        if instrument_type == InstrumentType.FOREX:
            from app.modules.fundamental_analysis.forex import analyze_forex

            return analyze_forex(request.symbol)

        if instrument_type == InstrumentType.COMMODITY:
            from app.modules.fundamental_analysis.commodities import analyze_commodity

            return await analyze_commodity(request.symbol)

        # INDEX
        from app.modules.fundamental_analysis.indices import analyze_index

        return analyze_index(request.symbol)

    except Exception:
        logger.exception("Fundamental analysis failed for %s", request.symbol)
        raise HTTPException(
            status_code=500,
            detail=f"Blad analizy fundamentalnej dla {request.symbol}.",
        ) from None
