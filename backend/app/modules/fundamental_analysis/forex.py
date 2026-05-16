"""Forex fundamental analyzer — compares macro data between currency pairs."""

import logging

from app.core.models import FundamentalData, InstrumentType

from .data_sources.macro_source import MacroDataSource, MacroIndicatorSource

logger = logging.getLogger(__name__)

# Map currency codes to macro indicator names
CURRENCY_RATE_MAP: dict[str, str] = {
    "USD": "fed_funds_rate",
    "EUR": "ecb_rate",
    "GBP": "boe_rate",
    "JPY": "boj_rate",
    "AUD": "rba_rate",
    "CAD": "boc_rate",
    "CHF": "snb_rate",
    "NZD": "rbnz_rate",
}

CURRENCY_CPI_MAP: dict[str, str] = {
    "USD": "cpi_us",
    "EUR": "cpi_eu",
    "GBP": "cpi_uk",
    "JPY": "cpi_jp",
    "AUD": "cpi_au",
    "CAD": "cpi_ca",
    "CHF": "cpi_ch",
    "NZD": "cpi_nz",
}

# Standard forex pair to (base, quote) mapping
PAIR_CURRENCIES: dict[str, tuple[str, str]] = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "USDCHF": ("USD", "CHF"),
    "AUDUSD": ("AUD", "USD"),
    "USDCAD": ("USD", "CAD"),
    "EURGBP": ("EUR", "GBP"),
    "EURJPY": ("EUR", "JPY"),
    "GBPJPY": ("GBP", "JPY"),
    "NZDUSD": ("NZD", "USD"),
    "AUDCAD": ("AUD", "CAD"),
    "AUDCHF": ("AUD", "CHF"),
    "AUDJPY": ("AUD", "JPY"),
    "CADJPY": ("CAD", "JPY"),
    "CHFJPY": ("CHF", "JPY"),
    "EURCHF": ("EUR", "CHF"),
    "EURAUD": ("EUR", "AUD"),
    "EURCAD": ("EUR", "CAD"),
    "GBPCAD": ("GBP", "CAD"),
    "GBPCHF": ("GBP", "CHF"),
    "AUDNZD": ("AUD", "NZD"),
    "NZDJPY": ("NZD", "JPY"),
    "NZDCAD": ("NZD", "CAD"),
    "NZDCHF": ("NZD", "CHF"),
    "EURNZD": ("EUR", "NZD"),
    "GBPNZD": ("GBP", "NZD"),
}


def _parse_pair(symbol: str) -> tuple[str, str]:
    """Extract base and quote currencies from a forex pair symbol."""
    clean = symbol.upper().replace("/", "").replace("-", "")
    if clean in PAIR_CURRENCIES:
        return PAIR_CURRENCIES[clean]
    # Fallback: first 3 chars = base, last 3 = quote
    if len(clean) == 6:
        return clean[:3], clean[3:]
    raise ValueError(f"Cannot parse forex pair: {symbol}")


def _compute_rate_differential(base_rate: float | None, quote_rate: float | None) -> float | None:
    """Higher interest rate attracts capital -> bullish for that currency.

    Positive differential means base currency has higher rate -> bullish for the pair.
    Returns None when either rate is unavailable.
    """
    if base_rate is None or quote_rate is None:
        return None
    return base_rate - quote_rate


def _compute_inflation_differential(base_cpi: float | None, quote_cpi: float | None) -> float | None:
    """Compare YoY inflation rates (%) between currencies.

    Lower inflation -> stronger currency.
    Positive means base has higher inflation -> bearish for the pair.
    Parameters are YoY inflation rates in %, not raw CPI index values.
    Returns None when either CPI is unavailable.
    """
    if base_cpi is None or quote_cpi is None:
        return None
    return base_cpi - quote_cpi


def _build_forex_summary(
    base: str,
    quote: str,
    score: float,
    components: int,
    rate_diff: float | None,
    inflation_diff: float | None,
) -> str:
    if components == 0:
        return f"Brak danych makro dla pary {base}/{quote}."
    if score > 10:
        direction = "bycza"
    elif score < -10:
        direction = "niedzwiedzia"
    else:
        direction = "neutralna"
    parts = []
    if rate_diff is not None:
        parts.append(f"roznica stop {base} vs {quote}: {rate_diff:+.2f}%")
    if inflation_diff is not None:
        parts.append(f"roznica inflacji: {inflation_diff:+.2f}pp")
    return f"Analiza fundamentalna {base}/{quote}: {direction} ({', '.join(parts)})."


async def analyze_forex(symbol: str, fred: MacroIndicatorSource | None = None) -> FundamentalData:
    """Run fundamental analysis for a forex pair.

    Compares interest rates, inflation between base and quote currencies.
    Returns FundamentalData with score from -100 (bearish) to +100 (bullish).
    """
    base, quote = _parse_pair(symbol)
    source = fred or MacroDataSource()

    # Fetch indicators for both currencies
    base_rate_name = CURRENCY_RATE_MAP.get(base)
    quote_rate_name = CURRENCY_RATE_MAP.get(quote)
    base_cpi_name = CURRENCY_CPI_MAP.get(base)
    quote_cpi_name = CURRENCY_CPI_MAP.get(quote)

    base_rate = await source.fetch_indicator(base_rate_name) if base_rate_name else None
    quote_rate = await source.fetch_indicator(quote_rate_name) if quote_rate_name else None
    base_cpi = await source.fetch_indicator(base_cpi_name) if base_cpi_name else None
    quote_cpi = await source.fetch_indicator(quote_cpi_name) if quote_cpi_name else None

    rate_diff: float | None = _compute_rate_differential(base_rate, quote_rate)
    inflation_diff: float | None = _compute_inflation_differential(base_cpi, quote_cpi)

    # Build indicators dict
    indicators: dict[str, float | str | None] = {
        "base_currency": base,
        "quote_currency": quote,
        f"{base}_interest_rate": base_rate,
        f"{quote}_interest_rate": quote_rate,
        "interest_rate_differential": rate_diff,
        f"{base}_inflation_yoy": base_cpi,
        f"{quote}_inflation_yoy": quote_cpi,
        "inflation_differential": inflation_diff,
    }

    # Scoring: rate differential contributes most (weight 60%), inflation inverted (weight 40%)
    score = 0.0
    components = 0

    if rate_diff is not None:
        # Clamp rate_diff contribution: each 1% diff = ~20 points, max 60
        rate_score = max(-60.0, min(60.0, rate_diff * 20.0))
        score += rate_score
        components += 1

    if inflation_diff is not None:
        # Higher base inflation = bearish for pair; each 1% = -10 points, max +-40
        inflation_score = max(-40.0, min(40.0, -inflation_diff * 10.0))
        score += inflation_score
        components += 1

    # Clamp final score
    score = max(-100.0, min(100.0, score))

    # Generate summary
    summary = _build_forex_summary(base, quote, score, components, rate_diff, inflation_diff)

    return FundamentalData(
        instrument_type=InstrumentType.FOREX,
        indicators=indicators,
        score=score,
        summary=summary,
    )
