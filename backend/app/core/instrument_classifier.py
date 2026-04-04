"""Instrument classification — shared symbol-to-type mapping."""

from app.core.models import InstrumentType

FOREX_PAIRS: set[str] = {
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
    "NZDUSD",
    "AUDCAD",
    "AUDCHF",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "EURCHF",
    "EURAUD",
    "EURCAD",
    "GBPCAD",
    "GBPCHF",
    "AUDNZD",
    "NZDJPY",
    "NZDCAD",
    "NZDCHF",
    "EURNZD",
    "GBPNZD",
}

COMMODITY_SYMBOLS: set[str] = {
    "GOLD",
    "XAUUSD",
    "SILVER",
    "XAGUSD",
    "OIL",
    "WTIUSD",
    "BRENT",
    "NATGAS",
    "COPPER",
    "PLATINUM",
    "PALLADIUM",
}

INDEX_SYMBOLS: set[str] = {
    "US500",
    "US30",
    "US100",
    "SPX",
    "NDX",
    "DJI",
    "DE40",
    "DAX",
    "EU50",
    "UK100",
    "FTSE",
    "JP225",
    "NIKKEI",
    "AU200",
    "CA60",
}


def classify_instrument(symbol: str) -> InstrumentType | None:
    """Auto-detect instrument type from symbol.

    Returns InstrumentType or None for unrecognized instruments.
    """
    clean = symbol.upper().replace("/", "").replace("-", "")
    if clean in FOREX_PAIRS:
        return InstrumentType.FOREX
    if clean in COMMODITY_SYMBOLS:
        return InstrumentType.COMMODITY
    if clean in INDEX_SYMBOLS:
        return InstrumentType.INDEX
    if len(clean) == 6 and clean.isalpha():
        return InstrumentType.FOREX
    return None
