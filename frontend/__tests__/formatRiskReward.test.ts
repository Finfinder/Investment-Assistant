import { describe, it, expect } from "vitest";
import { formatRiskReward } from "@/lib/format";

describe("formatRiskReward", () => {
  it.each([
    // Edge cases
    [null, "—", "zwraca myślnik dla null"],
    [0, "—", "zwraca myślnik dla zera"],
    [Infinity, "1:0.00", "zwraca 1:0.00 dla Infinity (1/Infinity = 0)"],
    [-Infinity, "1:0.00", "zwraca 1:0.00 dla -Infinity (1/-Infinity = -0)"],
    [NaN, "1:NaN", "zwraca 1:NaN dla NaN (aktualne zachowanie)"],
    // Normal cases
    [1, "1:1.00", "zwraca 1:1.00 dla ratio = 1"],
    [2, "1:0.50", "formatuje poprawnie dodatnie ratio"],
    [0.5, "1:2.00", "formatuje poprawnie ratio < 1"],
    [0.01, "1:100.00", "formatuje bardzo małą wartość"],
    [-2, "1:-0.50", "formatuje wartość ujemną"],
  ])("zwraca %s dla ratio = %s", (ratio, expected) => {
    expect(formatRiskReward(ratio)).toBe(expected);
  });
});
