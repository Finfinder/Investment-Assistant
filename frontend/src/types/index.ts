// TypeScript types mirroring backend Pydantic models

export type SignalType = "strong_sell" | "sell" | "neutral" | "buy" | "strong_buy";

export type Timeframe = "M15" | "H1" | "H4" | "D1";

export type InstrumentType = "forex" | "commodity" | "index";

export type PivotType = "classic" | "fibonacci" | "camarilla" | "woodie" | "demark";

export type AnalysisStatusType = "pending" | "running" | "completed" | "failed";

export type Direction = "long" | "short";

export type IndicatorPreset = "investing" | "tradingview";

export interface ChartLayerVisibility {
  ema: boolean;
  pivotPoints: boolean;
  fibonacci: boolean;
  patterns: boolean;
}

export const DEFAULT_LAYER_VISIBILITY: ChartLayerVisibility = {
  ema: true,
  pivotPoints: false,
  fibonacci: false,
  patterns: true,
};

export interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorValue {
  name: string;
  value: number | null;
  signal: SignalType;
}

export interface MovingAverage {
  period: number;
  sma_value: number | null;
  sma_signal: SignalType;
  ema_value: number | null;
  ema_signal: SignalType;
}

export interface PivotPoints {
  type: PivotType;
  pp: number | null;
  s1: number | null;
  s2: number | null;
  s3: number | null;
  r1: number | null;
  r2: number | null;
  r3: number | null;
}

export type PatternCategory =
  | "candlestick"
  | "chart_pattern"
  | "support_resistance"
  | "fibonacci"
  | "iki";

export interface PatternDetection {
  pattern_type: string;
  confidence: number;
  description: string;
  location: string;
  bullish: boolean;
  category: PatternCategory;
  detected_at_index: number | null;
  detected_at_timestamp: string;
  relevance_score: number;
  target_price: number | null;
  indication: string;
  reliability: number;
  detailed_description: string;
}

export interface FundamentalData {
  instrument_type: InstrumentType;
  indicators: Record<string, number | string | null>;
  score: number;
  summary: string;
}

export interface SignalSummary {
  ma_summary: SignalType;
  ma_buy_count: number;
  ma_sell_count: number;
  ma_neutral_count: number;
  indicators_summary: SignalType;
  indicators_buy_count: number;
  indicators_sell_count: number;
  indicators_neutral_count: number;
  overall_summary: SignalType;
  overall_buy_count: number;
  overall_sell_count: number;
  overall_neutral_count: number;
}

export interface StrategyEntry {
  direction: Direction;
  entry_condition: string;
  entry_price: number | null;
  stop_loss: number | null;
  tp1: number | null;
  tp2: number | null;
  confidence_pct: number;
  risk_reward_ratio: number | null;
  risk_reward_ratio_tp2: number | null;
}

export interface AnalysisReport {
  symbol: string;
  timeframe: Timeframe;
  timestamp: string;
  instrument_type: InstrumentType | null;
  ohlcv_data: OHLCVData[];
  technical_indicators: IndicatorValue[];
  moving_averages: MovingAverage[];
  pivot_points: PivotPoints[];
  patterns: PatternDetection[];
  fundamental: FundamentalData | null;
  signal_summary: SignalSummary | null;
  strategies: StrategyEntry[];
  strategy_skip_reason: string | null;
}

export interface AnalysisStatus {
  id: string;
  status: AnalysisStatusType;
  progress_pct: number;
  current_step: string;
  steps_completed: string[];
  error_message: string | null;
}

export interface AnalysisRequest {
  symbol: string;
  timeframe: Timeframe;
  preset: IndicatorPreset;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
}
