import { describe, it, expect } from "vitest";
import { riskRewardClass } from "@/lib/format";

describe("riskRewardClass", () => {
  // Uwaga: ujemne ratio zwraca "text-green-400" (gałąź <= 0.5).
  // To prawdopodobnie bug biznesowy — ujemne R/R nie powinno być klasyfikowane jako "bezpieczne".
  // TODO: Sprawdzić z biznesem czy ujemne ratio powinno rzucać error lub zwracać text-muted.
  it.each([
    ["null", null, "text-muted"],
    ["ratio 0 (granica zielone)", 0, "text-green-400"],
    ["ratio 0.5 (granica zielone)", 0.5, "text-green-400"],
    ["ratio 0.3 (zielone)", 0.3, "text-green-400"],
    ["ratio 0.001 (bardzo małe, zielone)", 0.001, "text-green-400"],
    ["ratio -0.5 (ujemne, aktualne zachowanie)", -0.5, "text-green-400"],
    ["ratio -1 (ujemne, zielone)", -1, "text-green-400"],
    ["ratio -Infinity (ujemne, zielone)", -Infinity, "text-green-400"],
    ["ratio 0.51 (granica żółte)", 0.51, "text-yellow-400"],
    ["ratio 0.7 (żółte)", 0.7, "text-yellow-400"],
    ["ratio 1 (żółte)", 1, "text-yellow-400"],
    ["ratio 100 (duże, żółte)", 100, "text-yellow-400"],
    ["ratio 1000 (bardzo duże, żółte)", 1000, "text-yellow-400"],
    ["ratio 1e6 (ekstremalnie duże, żółte)", 1e6, "text-yellow-400"],
    // NaN <= 0.5 → false → żółty (gałąź else)
    ["ratio NaN (żółte)", NaN, "text-yellow-400"],
    ["ratio Infinity (żółte)", Infinity, "text-yellow-400"],
  ])("zwraca %s dla %s", (_desc, ratio, expected) => {
    expect(riskRewardClass(ratio as number | null)).toBe(expected);
  });
});
