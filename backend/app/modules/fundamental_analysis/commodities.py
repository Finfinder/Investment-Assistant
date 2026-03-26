"""Commodities fundamental analyzer — COT data, USD strength, interest rates."""

import logging
from typing import Any

from app.core.models import FundamentalData, InstrumentType

from .data_sources.fmp_source import FmpEconomicSource
from .data_sources.fred_source import FredSource

logger = logging.getLogger(__name__)

# Map CFD symbols to COT report symbols used by FMP
COMMODITY_COT_MAP: dict[str, str] = {
    "GOLD": "GC",
    "XAUUSD": "GC",
    "SILVER": "SI",
    "XAGUSD": "SI",
    "OIL": "CL",
    "WTIUSD": "CL",
    "BRENT": "BZ",
    "NATGAS": "NG",
    "COPPER": "HG",
    "PLATINUM": "PL",
    "PALLADIUM": "PA",
}


def _score_cot(cot_data: dict[str, Any] | None) -> tuple[float, str]:
    """Score COT data: net speculative (non-commercial) positioning.

    Large net long speculative = bullish, large net short = bearish.
    Returns (score_component, description).
    """
    if cot_data is None:
        return 0.0, "Brak danych COT"

    net_nc = cot_data.get("net_non_commercial", 0)
    nc_long = cot_data.get("non_commercial_long", 1)
    nc_short = cot_data.get("non_commercial_short", 1)
    total = nc_long + nc_short

    if total == 0:
        return 0.0, "Brak pozycji spekulacyjnych"

    # Ratio: -1 (all short) to +1 (all long)
    ratio = net_nc / total
    score = ratio * 50  # max +-50 from COT

    change = cot_data.get("net_non_commercial_change")
    change_text = ""
    if change is not None:
        direction = "wzrost" if change > 0 else "spadek"
        change_text = f", zmiana tyg.: {direction} ({change:+d})"

    desc = f"COT net spekulacyjne: {net_nc:+d} (ratio: {ratio:+.2f}{change_text})"
    return score, desc


async def _score_usd_strength(fred: FredSource) -> tuple[float, str]:
    """Assess USD strength via Fed Funds rate and DXY proxy.

    Strong USD is generally bearish for dollar-denominated commodities.
    """
    fed_rate = await fred.fetch_indicator("fed_funds_rate")
    if fed_rate is None:
        return 0.0, "Brak danych o stopach Fed"

    # Higher fed rate -> stronger USD -> bearish for commodities (inverted)
    # Baseline: 3% = neutral, each 1% above = -10 pts, below = +10 pts
    baseline = 3.0
    score = -(fed_rate - baseline) * 10.0
    score = max(-30.0, min(30.0, score))

    desc = f"Stopa Fed: {fed_rate:.2f}% (USD {'silny' if fed_rate > baseline else 'slaby'})"
    return score, desc


async def _score_rates_environment(fred: FredSource) -> tuple[float, str]:
    """Real rates environment effect on commodities.

    Low/negative real rates -> bullish for hard assets (gold, silver).
    """
    fed_rate = await fred.fetch_indicator("fed_funds_rate")
    cpi = await fred.fetch_indicator("cpi_us")

    if fed_rate is None or cpi is None:
        return 0.0, "Brak danych o stopach realnych"

    # CPI is index, approximate YoY change as the raw value is index-based
    # For scoring we use the rate vs a CPI proxy
    # Negative real rate = bullish for commodities
    # Simple heuristic: if fed_rate < 3% => accommodative => bullish commodities
    real_score = max(-20.0, min(20.0, -(fed_rate - 2.5) * 8.0))

    desc = f"Srodowisko stop: Fed {fed_rate:.2f}%"
    return real_score, desc


async def analyze_commodity(
    symbol: str,
    fred: FredSource | None = None,
    fmp: FmpEconomicSource | None = None,
) -> FundamentalData:
    """Run fundamental analysis for a commodity CFD.

    Combines COT positioning, USD strength, and rate environment.
    Returns FundamentalData with score from -100 to +100.
    """
    fred_src = fred or FredSource()
    fmp_src = fmp or FmpEconomicSource()

    cot_symbol = COMMODITY_COT_MAP.get(symbol.upper(), symbol.upper())
    cot_data = await fmp_src.fetch_cot_report(cot_symbol)

    cot_score, cot_desc = _score_cot(cot_data)
    usd_score, usd_desc = await _score_usd_strength(fred_src)
    rates_score, rates_desc = await _score_rates_environment(fred_src)

    total_score = cot_score + usd_score + rates_score
    total_score = max(-100.0, min(100.0, total_score))

    indicators: dict[str, float | str | None] = {
        "cot_score": cot_score,
        "usd_strength_score": usd_score,
        "rates_environment_score": rates_score,
    }

    if cot_data:
        indicators["net_non_commercial"] = cot_data.get("net_non_commercial")
        indicators["net_commercial"] = cot_data.get("net_commercial")
        indicators["net_non_commercial_change"] = cot_data.get("net_non_commercial_change")

    direction = "bycza" if total_score > 10 else "niedzwiedzia" if total_score < -10 else "neutralna"
    summary = f"Analiza fundamentalna {symbol}: {direction}. {cot_desc}. {usd_desc}. {rates_desc}."

    return FundamentalData(
        instrument_type=InstrumentType.COMMODITY,
        indicators=indicators,
        score=total_score,
        summary=summary,
    )
