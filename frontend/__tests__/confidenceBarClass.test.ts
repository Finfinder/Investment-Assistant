import { describe, it, expect } from "vitest";
import { confidenceBarClass } from "@/lib/format";

describe("confidenceBarClass", () => {
  it("zwraca zielony dla pct >= 70", () => {
    expect(confidenceBarClass(70)).toBe("bg-green-400");
  });

  it("zwraca zielony dla pct > 70", () => {
    expect(confidenceBarClass(85)).toBe("bg-green-400");
  });

  it("zwraca zielony dla pct > 100", () => {
    expect(confidenceBarClass(150)).toBe("bg-green-400");
  });

  it("zwraca żółty dla pct == 40 (granica)", () => {
    expect(confidenceBarClass(40)).toBe("bg-yellow-400");
  });

  it("zwraca żółty dla pct między 40 a 70", () => {
    expect(confidenceBarClass(55)).toBe("bg-yellow-400");
  });

  it("zwraca żółty dla pct tuż poniżej 70", () => {
    expect(confidenceBarClass(69)).toBe("bg-yellow-400");
  });

  it("zwraca czerwony dla pct < 40", () => {
    expect(confidenceBarClass(25)).toBe("bg-red-400");
  });

  it("zwraca czerwony dla pct == 0", () => {
    expect(confidenceBarClass(0)).toBe("bg-red-400");
  });

  it("zwraca czerwony dla pct tuż poniżej 40", () => {
    expect(confidenceBarClass(39)).toBe("bg-red-400");
  });

  it("zwraca czerwony dla pct = 39.999 (poniżej 40)", () => {
    expect(confidenceBarClass(39.999)).toBe("bg-red-400");
  });

  it("zwraca czerwony dla NaN (aktualne zachowanie)", () => {
    expect(confidenceBarClass(NaN)).toBe("bg-red-400");
  });
});
