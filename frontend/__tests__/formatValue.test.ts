import { describe, it, expect } from "vitest";
import { formatValue } from "@/components/IndicatorTable/shared";

describe("formatValue", () => {
  it.each([
    [null, "—", "zwraca myślnik dla null"],
    [undefined, "—", "zwraca myślnik dla undefined"],
    [42, "42", "zwraca string bez miejsc po przecinku dla liczby całkowitej"],
    [0, "0", "zwraca string bez miejsc po przecinku dla zera"],
    [3.14159, "3.1416", "zwraca 4 miejsca po przecinku dla liczby dziesiętnej"],
    [-2.5, "-2.5000", "zwraca 4 miejsca po przecinku dla liczby ujemnej"],
    [75.25, "75.2500", "zwraca 4 miejsca po przecinku dla liczby dziesiętnej (procent)"],
    [1234.56, "1234.5600", "zwraca 4 miejsca po przecinku dla liczby dziesiętnej (kwota)"],
    [-0, "0", "zwraca '0' dla -0"],
    [NaN, "NaN", "zwraca 'NaN' dla NaN (aktualne zachowanie)"],
    [Infinity, "Infinity", "zwraca 'Infinity' dla Infinity (aktualne zachowanie)"],
  ] as const)("zwraca %s dla %s", (value, expected) => {
    expect(formatValue(value)).toBe(expected);
  });
});
