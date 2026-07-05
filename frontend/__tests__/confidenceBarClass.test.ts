import { describe, it, expect } from "vitest";
import { confidenceBarClass } from "@/lib/format";

describe("confidenceBarClass", () => {
  it.each([
    // Zielone (>= 70)
    [70, "bg-green-400", "zwraca zielony dla pct = 70 (granica)"],
    [85, "bg-green-400", "zwraca zielony dla pct > 70"],
    [150, "bg-green-400", "zwraca zielony dla pct > 100"],
    // Żółte (40 <= pct < 70)
    [40, "bg-yellow-400", "zwraca żółty dla pct = 40 (granica)"],
    [55, "bg-yellow-400", "zwraca żółty dla pct między 40 a 70"],
    [69, "bg-yellow-400", "zwraca żółty dla pct tuż poniżej 70"],
    // Czerwone (< 40)
    [0, "bg-red-400", "zwraca czerwony dla pct = 0"],
    [25, "bg-red-400", "zwraca czerwony dla pct < 40"],
    [39, "bg-red-400", "zwraca czerwony dla pct tuż poniżej 40"],
    [39.999, "bg-red-400", "zwraca czerwony dla pct = 39.999 (poniżej 40)"],
    // Edge case
    [NaN, "bg-red-400", "zwraca czerwony dla NaN (aktualne zachowanie)"],
  ])("zwraca %s dla pct = %s", (pct, expected) => {
    expect(confidenceBarClass(pct)).toBe(expected);
  });
});
