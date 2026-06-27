import { describe, it, expect } from "vitest";
import { riskRewardClass } from "@/lib/format";

describe("riskRewardClass", () => {
  it("zwraca text-muted dla null", () => {
    expect(riskRewardClass(null)).toBe("text-muted");
  });

  it("zwraca zielony dla ratio == 0.5 (granica)", () => {
    expect(riskRewardClass(0.5)).toBe("text-green-400");
  });

  it("zwraca zielony dla ratio < 0.5", () => {
    expect(riskRewardClass(0.3)).toBe("text-green-400");
  });

  it("zwraca zielony dla ratio == 0", () => {
    expect(riskRewardClass(0)).toBe("text-green-400");
  });

  it("zwraca żółty dla ratio > 0.5", () => {
    expect(riskRewardClass(0.7)).toBe("text-yellow-400");
  });

  it("zwraca żółty dla ratio == 1", () => {
    expect(riskRewardClass(1)).toBe("text-yellow-400");
  });

  it("zwraca zielony dla ratio ujemnego (aktualne zachowanie)", () => {
    expect(riskRewardClass(-0.5)).toBe("text-green-400");
  });

  it.each([
    ["null", null, "text-muted"],
    ["ratio 0 (granica zielone)", 0, "text-green-400"],
    ["ratio 0.5 (granica zielone)", 0.5, "text-green-400"],
    ["ratio 0.3 (zielone)", 0.3, "text-green-400"],
    ["ratio 0.001 (bardzo małe, zielone)", 0.001, "text-green-400"],
    ["ratio -1 (ujemne, zielone)", -1, "text-green-400"],
    ["ratio -Infinity (ujemne, zielone)", -Infinity, "text-green-400"],
    ["ratio 0.51 (granica żółte)", 0.51, "text-yellow-400"],
    ["ratio 1 (żółte)", 1, "text-yellow-400"],
    ["ratio 100 (duże, żółte)", 100, "text-yellow-400"],
    ["ratio 1000 (bardzo duże, żółte)", 1000, "text-yellow-400"],
    ["ratio 1e6 (ekstremalnie duże, żółte)", 1e6, "text-yellow-400"],
    ["ratio Infinity (żółte)", Infinity, "text-yellow-400"],
    ["ratio NaN (żółte)", NaN, "text-yellow-400"],
  ])("zwraca %s dla %s", (_desc, ratio, expected) => {
    expect(riskRewardClass(ratio as number | null)).toBe(expected);
  });
});
