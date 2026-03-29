from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SignalType(StrEnum):
    STRONG_SELL = "strong_sell"
    SELL = "sell"
    NEUTRAL = "neutral"
    BUY = "buy"
    STRONG_BUY = "strong_buy"


class Timeframe(StrEnum):
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class InstrumentType(StrEnum):
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"


class PivotType(StrEnum):
    CLASSIC = "classic"
    FIBONACCI = "fibonacci"
    CAMARILLA = "camarilla"
    WOODIE = "woodie"
    DEMARK = "demark"


class AnalysisStatusType(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"


class IndicatorPreset(StrEnum):
    INVESTING = "investing"
    TRADINGVIEW = "tradingview"


# --- Data Models ---


class OHLCVData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class IndicatorValue(BaseModel):
    name: str
    value: float | None = None
    signal: SignalType = SignalType.NEUTRAL


class MovingAverage(BaseModel):
    period: int
    sma_value: float | None = None
    sma_signal: SignalType = SignalType.NEUTRAL
    ema_value: float | None = None
    ema_signal: SignalType = SignalType.NEUTRAL


class PivotPoints(BaseModel):
    type: PivotType
    pp: float | None = None
    s1: float | None = None
    s2: float | None = None
    s3: float | None = None
    r1: float | None = None
    r2: float | None = None
    r3: float | None = None


class PatternDetection(BaseModel):
    pattern_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str = ""
    location: str = ""
    bullish: bool = True


class FundamentalData(BaseModel):
    instrument_type: InstrumentType
    indicators: dict[str, float | str | None] = Field(default_factory=dict)
    score: float = Field(ge=-100.0, le=100.0, default=0.0)
    summary: str = ""


class SignalSummary(BaseModel):
    ma_summary: SignalType = SignalType.NEUTRAL
    ma_buy_count: int = 0
    ma_sell_count: int = 0
    ma_neutral_count: int = 0
    indicators_summary: SignalType = SignalType.NEUTRAL
    indicators_buy_count: int = 0
    indicators_sell_count: int = 0
    indicators_neutral_count: int = 0
    overall_summary: SignalType = SignalType.NEUTRAL
    overall_buy_count: int = 0
    overall_sell_count: int = 0
    overall_neutral_count: int = 0


class StrategyEntry(BaseModel):
    direction: Direction
    entry_condition: str = ""
    entry_price: float | None = None
    stop_loss: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    confidence_pct: float = Field(ge=0.0, le=100.0, default=0.0)


class AnalysisReport(BaseModel):
    symbol: str
    timeframe: Timeframe
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    instrument_type: InstrumentType | None = None
    ohlcv_data: list[OHLCVData] = Field(default_factory=list)
    technical_indicators: list[IndicatorValue] = Field(default_factory=list)
    moving_averages: list[MovingAverage] = Field(default_factory=list)
    pivot_points: list[PivotPoints] = Field(default_factory=list)
    patterns: list[PatternDetection] = Field(default_factory=list)
    fundamental: FundamentalData | None = None
    signal_summary: SignalSummary | None = None
    strategies: list[StrategyEntry] = Field(default_factory=list)
    strategy_skip_reason: str | None = None


class AnalysisStatus(BaseModel):
    id: str
    status: AnalysisStatusType = AnalysisStatusType.PENDING
    progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    current_step: str = ""
    steps_completed: list[str] = Field(default_factory=list)
    error_message: str | None = None
