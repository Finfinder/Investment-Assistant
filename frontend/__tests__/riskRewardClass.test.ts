import { describe, it, expect } from "vitest";
import { riskRewardClass } from "@/lib/format";

describe("riskRewardClass", () => {
  // Ujemne R/R jest poprawnie klasyfikowane jako niekorzystne (czerwone) — poprawka Issue #126.
  it.each([
    ["null", null, "text-muted"],
    ["ratio 0 (granica zielone)", 0, "text-green-400"],
    ["ratio 0.5 (granica zielone)", 0.5, "text-green-400"],
    ["ratio 0.3 (zielone)", 0.3, "text-green-400"],
    ["ratio 0.001 (bardzo małe, zielone)", 0.001, "text-green-400"],
    ["ratio -0.5 (ujemne, czerwone)", -0.5, "text-red-400"],
    ["ratio -1 (ujemne, czerwone)", -1, "text-red-400"],
    ["ratio -Infinity (nie-finite, destrukcyjne)", -Infinity, "text-danger"],
    ["ratio 0.51 (tuż powyżej progu, żółte)", 0.51, "text-yellow-400"],
    ["ratio 0.7 (żółte)", 0.7, "text-yellow-400"],
    ["ratio 1 (żółte)", 1, "text-yellow-400"],
    ["ratio 100 (duże, żółte)", 100, "text-yellow-400"],
    ["ratio 1000 (bardzo duże, żółte)", 1000, "text-yellow-400"],
    ["ratio 1e6 (ekstremalnie duże, żółte)", 1e6, "text-yellow-400"],
    // NaN i Infinity to nie-finite → text-danger (błędne dane, poprawka Issue #125)
    ["ratio NaN (nie-finite, destrukcyjne)", NaN, "text-danger"],
    ["ratio Infinity (nie-finite, destrukcyjne)", Infinity, "text-danger"],
  ] as const)("zwraca %s dla %s", (_desc, ratio, expected) => {
    expect(riskRewardClass(ratio)).toBe(expected);
  });
});
