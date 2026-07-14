import { describe, it, expect } from "vitest";
import { makeStrategyEntry } from "./factories";
import type { StrategyEntry } from "@/types";

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
