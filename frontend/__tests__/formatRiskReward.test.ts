import { describe, it, expect } from "vitest";
import { formatRiskReward } from "@/lib/format";

describe("formatRiskReward", () => {
  it("zwraca pomić dla null", () => {
    expect(formatRiskReward(null)).toBe("—");
  });

  it("zwraca pomić dla zera", () => {
    expect(formatRiskReward(0)).toBe("—");
  });

  it("zwraca 1:1.00 dla ratio == 1", () => {
    expect(formatRiskReward(1)).toBe("1:1.00");
  });

  it("formatuje poprawnie dodatnie ratio", () => {
    expect(formatRiskReward(2)).toBe("1:0.50");
  });

  it("formatuje poprawnie ratio < 1", () => {
    expect(formatRiskReward(0.5)).toBe("1:2.00");
  });

  it("formatuje bardzo małą wartość", () => {
    expect(formatRiskReward(0.01)).toBe("1:100.00");
  });

  it("formatuje wartość ujemną", () => {
    expect(formatRiskReward(-2)).toBe("1:-0.50");
  });
});
