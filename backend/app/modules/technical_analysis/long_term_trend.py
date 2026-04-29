from app.core.models import IndicatorPreset, LongTermTrend, OHLCVData, SignalType
from app.modules.technical_analysis.indicators import calculate_indicators
from app.modules.technical_analysis.moving_averages import calculate_moving_averages
from app.modules.technical_analysis.presets import get_preset_params
from app.modules.technical_analysis.summary import calculate_summaries

_TREND_SUMMARY_LABELS: dict[SignalType, str] = {
    SignalType.STRONG_BUY: "Silny trend wzrostowy",
    SignalType.BUY: "Trend wzrostowy",
    SignalType.NEUTRAL: "Trend boczny",
    SignalType.SELL: "Trend spadkowy",
    SignalType.STRONG_SELL: "Silny trend spadkowy",
}


def build_long_term_trend(ohlcv: list[OHLCVData], preset: IndicatorPreset) -> LongTermTrend | None:
    if not ohlcv:
        return None

    params = get_preset_params(preset)

    try:
        indicators = calculate_indicators(ohlcv, params)
    except Exception:
        indicators = []

    try:
        moving_averages = calculate_moving_averages(ohlcv)
    except Exception:
        moving_averages = []

    if not indicators and not moving_averages:
        return None

    try:
        summary = calculate_summaries(indicators, moving_averages)
    except Exception:
        return None

    return LongTermTrend(
        signal=summary.overall_summary,
        summary=_TREND_SUMMARY_LABELS[summary.overall_summary],
    )
