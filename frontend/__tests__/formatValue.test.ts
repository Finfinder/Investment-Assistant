import { describe, it, expect } from "vitest";
import { formatValue } from "@/components/IndicatorTable/shared";

describe("formatValue", () => {
  it("zwraca myślnik dla null", () => {
    expect(formatValue(null)).toBe("—");
  });

  it("zwraca myślnik dla undefined", () => {
    expect(formatValue(undefined)).toBe("—");
  });

  it("zwraca string bez miejsc po przecinku dla liczby całkowitej", () => {
    expect(formatValue(42)).toBe("42");
  });

  it("zwraca string bez miejsc po przecinku dla zera", () => {
    expect(formatValue(0)).toBe("0");
  });

  it("zwraca 4 miejsca po przecinku dla liczby dziesiętnej", () => {
    expect(formatValue(3.14159)).toBe("3.1416");
  });

  it("zwraca 4 miejsca po przecinku dla liczby ujemnej", () => {
    expect(formatValue(-2.5)).toBe("-2.5000");
  });

  it("zwraca 4 miejsca po przecinku dla liczby dziesiętnej (procent)", () => {
    expect(formatValue(75.25)).toBe("75.2500");
  });

  it("zwraca 4 miejsca po przecinku dla liczby dziesiętnej (kwota)", () => {
    expect(formatValue(1234.56)).toBe("1234.5600");
  });

  it("zwraca '0' dla -0", () => {
    expect(formatValue(-0)).toBe("0");
  });

  it("zwraca 'NaN' dla NaN (aktualne zachowanie)", () => {
    expect(formatValue(NaN)).toBe("NaN");
  });

  it("zwraca 'Infinity' dla Infinity (aktualne zachowanie)", () => {
    expect(formatValue(Infinity)).toBe("Infinity");
  });
});
