import { describe, it, expect } from "vitest";
import { makeStrategyEntry, makeAnalysisReport } from "./factories";
import type { AnalysisReport, StrategyEntry } from "@/types";

describe("makeStrategyEntry", () => {
  it("bez argumentów zwraca poprawny, w pełni wypełniony obiekt", () => {
    const entry = makeStrategyEntry();

    // Każde pole interfejsu StrategyEntry musi być zdefiniowane (brak undefined).
    const keys: (keyof StrategyEntry)[] = [
      "direction",
      "entry_condition",
      "entry_price",
      "stop_loss",
      "tp1",
      "tp2",
      "confidence_pct",
      "risk_reward_ratio",
      "risk_reward_ratio_tp2",
    ];
    for (const key of keys) {
      expect(entry[key]).not.toBeUndefined();
    }
    expect(entry.direction).toBe("long");
    expect(entry.confidence_pct).toBe(50);
  });

  it("nadpisuje tylko podane pola, zachowując domyślne wartości pozostałych", () => {
    const entry = makeStrategyEntry({ direction: "short", confidence_pct: 80 });

    expect(entry.direction).toBe("short");
    expect(entry.confidence_pct).toBe(80);
    // Niepodane pola zachowują wartości domyślne.
    expect(entry.entry_condition).toBe("");
    expect(entry.entry_price).toBe(1.1);
    expect(entry.risk_reward_ratio).toBe(1);
  });
});

describe("makeAnalysisReport", () => {
  it("bez argumentów zwraca poprawny, w pełni wypełniony obiekt", () => {
    const report = makeAnalysisReport();

    // Każde pole interfejsu AnalysisReport musi być zdefiniowane (brak undefined).
    const keys: (keyof AnalysisReport)[] = [
      "symbol",
      "timeframe",
      "timestamp",
      "instrument_type",
      "timeframe_context",
      "ohlcv_data",
      "technical_indicators",
      "moving_averages",
      "pivot_points",
      "patterns",
      "pattern_scanner_results",
      "long_term_trend",
      "fundamental",
      "signal_summary",
      "strategies",
      "strategy_skip_reason",
    ];
    for (const key of keys) {
      expect(report[key]).not.toBeUndefined();
    }
    expect(report.symbol).toBe("EURUSD");
    expect(report.timeframe).toBe("H1");
  });

  it("agreguje listę strategii przez makeStrategyEntry", () => {
    const report = makeAnalysisReport();

    // Domyślnie strategies to niepusta tablica zbudowana przez makeStrategyEntry.
    expect(Array.isArray(report.strategies)).toBe(true);
    expect(report.strategies).toHaveLength(1);
    expect(report.strategies[0].direction).toBe("long");
    expect(report.strategies[0].confidence_pct).toBe(50);
  });

  it("nadpisuje tylko podane pola, zachowując domyślne wartości pozostałych", () => {
    const report = makeAnalysisReport({ symbol: "GBPUSD", timeframe: "D1" });

    expect(report.symbol).toBe("GBPUSD");
    expect(report.timeframe).toBe("D1");
    // Niepodane pola zachowują wartości domyślne.
    expect(report.instrument_type).toBe("forex");
    expect(report.strategies).toHaveLength(1);
    // Nadpisanie strategies zastępuje całą tablicę.
    const custom = makeAnalysisReport({
      strategies: [makeStrategyEntry({ direction: "short", confidence_pct: 80 })],
    });
    expect(custom.strategies).toHaveLength(1);
    expect(custom.strategies[0].direction).toBe("short");
    expect(custom.strategies[0].confidence_pct).toBe(80);
  });

  it("ignoruje overridy o wartości undefined, zachowując domyślne wartości", () => {
    const report = makeAnalysisReport({ symbol: undefined, timeframe: undefined });

    // Wartości undefined są odfiltrowywane — zachowane są domyślne.
    expect(report.symbol).toBe("EURUSD");
    expect(report.timeframe).toBe("H1");
  });

  it("zwraca niezależne kopie zagnieżdżonych obiektów i tablic (brak współdzielonych referencji)", () => {
    const first = makeAnalysisReport();
    const second = makeAnalysisReport();

    // Mutacja zagnieżdżonej tablicy/obiektu w jednym raporcie nie przecieka do drugiego.
    first.ohlcv_data.push({
      timestamp: new Date().toISOString(),
      open: 1.2,
      high: 1.3,
      low: 1.1,
      close: 1.25,
      volume: 999,
    });
    first.strategies.push(makeStrategyEntry({ direction: "short" }));
    first.timeframe_context.long_term_trend_label = "daily";

    expect(second.ohlcv_data).toHaveLength(30);
    expect(second.strategies).toHaveLength(1);
    expect(second.timeframe_context.long_term_trend_label).toBe("weekly");
  });
});
