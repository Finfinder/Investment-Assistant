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
});
