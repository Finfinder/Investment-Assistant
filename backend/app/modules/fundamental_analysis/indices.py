"""Indices fundamental analyzer — regional macro data for stock indices."""

import logging

from app.core.models import FundamentalData, InstrumentType

from .data_sources.macro_source import MacroDataSource, MacroIndicatorSource

logger = logging.getLogger(__name__)

# Map index symbols to regions
INDEX_REGION_MAP: dict[str, str] = {
    "US500": "US",
    "US30": "US",
    "US100": "US",
    "SPX": "US",
    "NDX": "US",
    "DJI": "US",
    "DE40": "EU",
    "DAX": "EU",
    "EU50": "EU",
    "UK100": "UK",
    "FTSE": "UK",
    "JP225": "JP",
    "NIKKEI": "JP",
    "AU200": "AU",
    "CA60": "CA",
}

# Macro indicators per region
REGION_INDICATORS: dict[str, dict[str, str]] = {
    "US": {
        "interest_rate": "fed_funds_rate",
        "cpi": "cpi_us",
        "unemployment": "unemployment_us",
        "gdp": "gdp_us",
    },
    "EU": {
        "interest_rate": "ecb_rate",
        "cpi": "cpi_eu",
    },
    "UK": {
        "interest_rate": "boe_rate",
        "cpi": "cpi_uk",
    },
    "JP": {
        "interest_rate": "boj_rate",
        "cpi": "cpi_jp",
    },
    "AU": {
        "interest_rate": "rba_rate",
        "cpi": "cpi_au",
    },
    "CA": {
        "interest_rate": "boc_rate",
        "cpi": "cpi_ca",
    },
}


def _score_interest_rate(rate: float | None) -> tuple[float, str]:
    """Lower rates -> easier monetary policy -> bullish for equities."""
    if rate is None:
        return 0.0, "Brak danych o stopach procentowych"

    # Baseline: 3% = neutral; below = bullish, above = bearish
    baseline = 3.0
    score = -(rate - baseline) * 12.0
    score = max(-40.0, min(40.0, score))

    if rate < baseline:
        stance = "luzna"
    elif rate > baseline:
        stance = "restrykcyjna"
    else:
        stance = "neutralna"
    desc = f"Stopa procentowa: {rate:.2f}% (polityka {stance})"
    return score, desc


def _score_unemployment(unemployment: float | None) -> tuple[float, str]:
    """Low unemployment -> strong economy -> bullish, but too low may signal overheating."""
    if unemployment is None:
        return 0.0, ""

    # Baseline: 5% = neutral
    baseline = 5.0
    score = -(unemployment - baseline) * 6.0
    score = max(-20.0, min(20.0, score))

    condition = "silny" if unemployment < baseline else "slaby"
    desc = f"Bezrobocie: {unemployment:.1f}% (rynek pracy {condition})"
    return score, desc


def _score_inflation(cpi_yoy: float | None) -> tuple[float, str]:
    """Score inflation based on CPI YoY% deviation from the 2% central bank target.

    Above target = bearish (tighter policy ahead), below = mildly bullish.
    """
    if cpi_yoy is None:
        return 0.0, ""

    target = 2.0
    deviation = cpi_yoy - target
    # Asymmetric: above target hurts more (-8 per pp) than below helps (+4 per pp)
    score = -deviation * 8.0 if deviation > 0 else -deviation * 4.0
    score = max(-30.0, min(30.0, score))

    return score, f"Inflacja CPI: {cpi_yoy:.1f}% r/r"


async def analyze_index(symbol: str, fred: MacroIndicatorSource | None = None) -> FundamentalData:
    """Run fundamental analysis for a stock index.

    Evaluates regional macro: interest rates, unemployment, GDP.
    Returns FundamentalData with score from -100 to +100.
    """
    source = fred or MacroDataSource()
    clean_symbol = symbol.upper().replace("/", "")

    region = INDEX_REGION_MAP.get(clean_symbol)
    if not region:
        return FundamentalData(
            instrument_type=InstrumentType.INDEX,
            indicators={"region": None},
            score=0.0,
            summary=f"Nieznany indeks {symbol} - brak mapowania regionu.",
        )

    region_keys = REGION_INDICATORS.get(region, {})

    # Fetch regional indicators
    rate = await source.fetch_indicator(region_keys["interest_rate"]) if "interest_rate" in region_keys else None
    cpi = await source.fetch_indicator(region_keys["cpi"]) if "cpi" in region_keys else None
    unemp_key = region_keys.get("unemployment", "")
    unemployment = await source.fetch_indicator(unemp_key) if "unemployment" in region_keys else None
    gdp_key = region_keys.get("gdp", "")
    gdp = await source.fetch_indicator(gdp_key) if "gdp" in region_keys else None

    rate_score, rate_desc = _score_interest_rate(rate)
    unemp_score, unemp_desc = _score_unemployment(unemployment)
    cpi_score, cpi_desc = _score_inflation(cpi)

    total_score = rate_score + unemp_score + cpi_score
    total_score = max(-100.0, min(100.0, total_score))

    indicators: dict[str, float | str | None] = {
        "region": region,
        "interest_rate": rate,
        "inflation_yoy": cpi,
        "unemployment": unemployment,
        "gdp": gdp,
        "rate_score": rate_score,
        "unemployment_score": unemp_score,
    }

    if total_score > 10:
        direction = "bycza"
    elif total_score < -10:
        direction = "niedzwiedzia"
    else:
        direction = "neutralna"
    parts = [rate_desc]
    if unemp_desc:
        parts.append(unemp_desc)
    if cpi_desc:
        parts.append(cpi_desc)

    summary = f"Analiza fundamentalna {symbol} (region {region}): {direction}. {'. '.join(parts)}."

    return FundamentalData(
        instrument_type=InstrumentType.INDEX,
        indicators=indicators,
        score=total_score,
        summary=summary,
    )
