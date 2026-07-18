import type { AnalysisReport, StrategyEntry } from "@/types";

const DEFAULT_STRATEGY_ENTRY: StrategyEntry = {
  direction: "long",
  entry_condition: "",
  entry_price: 1.1,
  stop_loss: 1.0,
  tp1: 1.2,
  tp2: 1.3,
  confidence_pct: 50,
  risk_reward_ratio: 1,
  risk_reward_ratio_tp2: 1,
};

export function makeStrategyEntry(overrides: Partial<StrategyEntry> = {}): StrategyEntry {
  const definedOverrides = Object.fromEntries(
    Object.entries(overrides).filter(([, value]) => value !== undefined),
  ) as Partial<StrategyEntry>;
  return { ...DEFAULT_STRATEGY_ENTRY, ...definedOverrides };
}

const DEFAULT_ANALYSIS_REPORT: AnalysisReport = {
  symbol: "EURUSD",
  timeframe: "H1",
  timestamp: new Date().toISOString(),
  instrument_type: "forex",
  timeframe_context: {
    pivot_points_timeframe: "D1",
    pattern_scanner_timeframes: ["D1", "H1", "M15"],
    long_term_trend_label: "weekly",
  },
  ohlcv_data: Array.from({ length: 30 }, (_, i) => ({
    timestamp: new Date(Date.now() - (30 - i) * 3600000).toISOString(),
    open: 1.1 + i * 0.001,
    high: 1.1 + i * 0.001 + 0.002,
    low: 1.1 + i * 0.001 - 0.001,
    close: 1.1 + i * 0.001 + 0.001,
    volume: 1000 + i * 100,
  })),
  technical_indicators: [
    { name: "RSI(14)", value: 55.3, signal: "neutral" },
    { name: "STOCH.K(9)", value: 65, signal: "buy" },
    { name: "CCI(14)", value: 45.2, signal: "neutral" },
    { name: "ADX(14)", value: 28.5, signal: "neutral" },
    { name: "AO", value: 0.0035, signal: "buy" },
    { name: "Momentum(10)", value: 0.012, signal: "buy" },
    { name: "MACD(12,26,9)", value: 0.0012, signal: "buy" },
    { name: "Williams %R(14)", value: -35.2, signal: "neutral" },
    { name: "UO(7,14,28)", value: 52.1, signal: "neutral" },
    { name: "ATR(14)", value: 0.0045, signal: "neutral" },
    { name: "BBP(13)", value: 0.0023, signal: "buy" },
    { name: "STOCHRSI.K(14)", value: 72.5, signal: "neutral" },
    { name: "ROC(15)", value: 1.25, signal: "buy" },
  ],
  moving_averages: [
    { period: 10, sma_value: 1.105, sma_signal: "buy", ema_value: 1.106, ema_signal: "buy" },
    { period: 20, sma_value: 1.1, sma_signal: "neutral", ema_value: 1.101, ema_signal: "neutral" },
    { period: 50, sma_value: 1.095, sma_signal: "sell", ema_value: 1.096, ema_signal: "sell" },
  ],
  pivot_points: [
    { type: "classic", pp: 1.105, s1: 1.1, s2: 1.095, s3: 1.09, r1: 1.11, r2: 1.115, r3: 1.12 },
  ],
  patterns: [
    {
      pattern_type: "Hammer",
      confidence: 0.85,
      description: "Formacja młota",
      location: "emerging",
      bullish: true,
      category: "candlestick",
      timeframe: "H1",
      detected_at_index: 29,
      detected_at_timestamp: new Date().toISOString(),
      relevance_score: 0.9,
      target_price: null,
      indication: "Odwrót bycza",
      reliability: 2,
      detailed_description:
        "Formacja młota pojawia się po trendzie spadkowym i sygnalizuje potencjalne odwrócenie na wzrostowy.",
    },
  ],
  pattern_scanner_results: [
    {
      pattern_type: "Hammer",
      category: "candlestick",
      bullish: true,
      confidence: 0.85,
      timeframes: ["D1", "H1"],
      representative_pattern: {
        pattern_type: "Hammer",
        confidence: 0.85,
        description: "Formacja młota",
        location: "emerging",
        bullish: true,
        category: "candlestick",
        timeframe: "H1",
        detected_at_index: 29,
        detected_at_timestamp: new Date().toISOString(),
        relevance_score: 0.9,
        target_price: null,
        indication: "Odwrót bycza",
        reliability: 2,
        detailed_description:
          "Formacja młota pojawia się po trendzie spadkowym i sygnalizuje potencjalne odwrócenie na wzrostowy.",
      },
    },
    {
      pattern_type: "Ascending Triangle",
      category: "chart_pattern",
      bullish: true,
      confidence: 0.72,
      timeframes: ["M15"],
      representative_pattern: {
        pattern_type: "Ascending Triangle",
        confidence: 0.72,
        description: "Formacja kontynuacji z rosnącymi minimami.",
        location: "completed",
        bullish: true,
        category: "chart_pattern",
        timeframe: "M15",
        detected_at_index: 18,
        detected_at_timestamp: new Date().toISOString(),
        relevance_score: 0.68,
        target_price: 1.128,
        indication: "Kontynuacja wzrostu",
        reliability: 2,
        detailed_description:
          "Trójkąt zwyżkujący sygnalizuje możliwość wybicia zgodnego z kierunkiem wcześniejszego trendu.",
      },
    },
    {
      pattern_type: "Doji",
      category: "candlestick",
      bullish: false,
      confidence: 0.55,
      timeframes: ["H1"],
      representative_pattern: {
        pattern_type: "Doji",
        confidence: 0.55,
        description: "Świeca Doji sygnalizująca niepewność rynku.",
        location: "current",
        bullish: false,
        category: "candlestick",
        timeframe: "H1",
        detected_at_index: 25,
        detected_at_timestamp: new Date().toISOString(),
        relevance_score: 0.45,
        target_price: null,
        indication: "Niedźwiedź",
        reliability: 1,
        detailed_description:
          "Doji pojawia się, gdy otwarte i zamknięcie ceny są bliskie sobie, co sugeruje równowagę między kupującymi a sprzedającymi.",
      },
    },
  ],
  long_term_trend: {
    signal: "buy",
    summary: "Trend wzrostowy",
    source_label: "weekly",
  },
  fundamental: {
    instrument_type: "forex",
    indicators: { interest_rate_diff: 1.5 },
    score: 6.5,
    summary: "Umiarkowanie pozytywne dane fundamentalne",
  },
  signal_summary: {
    ma_summary: "buy",
    ma_buy_count: 5,
    ma_sell_count: 2,
    ma_neutral_count: 3,
    indicators_summary: "buy",
    indicators_buy_count: 5,
    indicators_sell_count: 2,
    indicators_neutral_count: 6,
    overall_summary: "buy",
    overall_buy_count: 10,
    overall_sell_count: 4,
    overall_neutral_count: 9,
  },
  strategies: [makeStrategyEntry()],
  strategy_skip_reason: null,
};

export function makeAnalysisReport(overrides: Partial<AnalysisReport> = {}): AnalysisReport {
  const definedOverrides = Object.fromEntries(
    Object.entries(overrides).filter(([, value]) => value !== undefined),
  ) as Partial<AnalysisReport>;
  return { ...DEFAULT_ANALYSIS_REPORT, ...definedOverrides };
}
