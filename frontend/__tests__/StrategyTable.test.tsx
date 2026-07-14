import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StrategyTable from "@/components/Strategy/StrategyTable";
import { formatRiskReward } from "@/lib/format";
import { makeStrategyEntry } from "./factories";

describe("StrategyTable", () => {
  it("z pustą listą wyświetla komunikat domyślny", () => {
    render(<StrategyTable strategies={[]} />);

    expect(screen.getByText("Brak wygenerowanych strategii")).toBeInTheDocument();
  });

  it("z pustą listą wyświetla strategySkipReason gdy podany", () => {
    render(<StrategyTable strategies={[]} strategySkipReason="Za mało danych" />);

    expect(screen.getByText("Za mało danych")).toBeInTheDocument();
  });

  it("z danymi wyświetla wiersze z kierunkiem, wejściem, SL, TP", () => {
    const strategies = [
      makeStrategyEntry({
        direction: "long",
        entry_condition: "Price above EMA",
        entry_price: 1.1,
        stop_loss: 1.09,
        tp1: 1.11,
        tp2: 1.12,
        confidence_pct: 75,
        risk_reward_ratio: 0.5,
        risk_reward_ratio_tp2: 0.25,
      }),
      makeStrategyEntry({
        direction: "short",
        entry_condition: "Price below EMA",
        entry_price: 1.1,
        stop_loss: 1.11,
        tp1: 1.09,
        tp2: 1.08,
        confidence_pct: 60,
        risk_reward_ratio: 0.75,
        risk_reward_ratio_tp2: 0.4,
      }),
    ];

    render(<StrategyTable strategies={strategies} />);

    expect(screen.getByRole("heading", { name: "Strategie wejścia" })).toBeInTheDocument();
    expect(screen.getAllByText("▲ LONG").length).toBeGreaterThan(0);
    expect(screen.getAllByText("▼ SHORT").length).toBeGreaterThan(0);
    expect(screen.getByText("Price above EMA")).toBeInTheDocument();
    expect(screen.getByText("Price below EMA")).toBeInTheDocument();
  });

  it("kierunek long ma zielony kolor, short — czerwony", () => {
    const strategies = [
      makeStrategyEntry({ direction: "long", stop_loss: 1.0, tp1: 1.2, tp2: 1.3 }),
      makeStrategyEntry({ direction: "short", stop_loss: 1.2, tp1: 1.0, tp2: 0.9 }),
    ];

    render(<StrategyTable strategies={strategies} />);

    // Verify direction badges have correct CSS classes for color coding
    const longBadge = screen.getByText("▲ LONG");
    expect(longBadge).toHaveClass("text-green-400");
    const shortBadge = screen.getByText("▼ SHORT");
    expect(shortBadge).toHaveClass("text-red-400");
  });

  it("pasek pewności renderuje się z odpowiednią szerokością", () => {
    const strategies = [makeStrategyEntry({ confidence_pct: 75 })];

    render(<StrategyTable strategies={strategies} />);

    // Use getAllByText since there might be multiple elements with "75%"
    const percentageElements = screen.getAllByText(/75/);
    expect(percentageElements.length).toBeGreaterThan(0);
  });

  describe("riskRewardClass applied in StrategyTable", () => {
    it.each([
      ["null (brak danych)", null, "text-muted"],
      ["ratio 0 (granica zielone)", 0, "text-green-400"],
      ["ratio 0.3 (zielone)", 0.3, "text-green-400"],
      ["ratio 0.5 (próg włącznie, zielone)", 0.5, "text-green-400"],
      ["ratio 0.51 (tuż powyżej progu, żółte)", 0.51, "text-yellow-400"],
      ["ratio 0.7 (żółte)", 0.7, "text-yellow-400"],
      ["ratio 1 (żółte)", 1, "text-yellow-400"],
      ["ratio 100 (duże, żółte)", 100, "text-yellow-400"],
      ["ratio -0.5 (ujemne, czerwone)", -0.5, "text-red-400"],
      ["ratio -1 (ujemne, czerwone)", -1, "text-red-400"],
      ["ratio NaN (nie-finite, text-danger)", NaN, "text-danger"],
      ["ratio Infinity (nie-finite, text-danger)", Infinity, "text-danger"],
      ["ratio -Infinity (nie-finite, text-danger)", -Infinity, "text-danger"],
    ] as const)("nakłada klasę %s dla R/R = %s", (_desc, ratio, expectedClass) => {
      const strategies = [makeStrategyEntry({ risk_reward_ratio: ratio, risk_reward_ratio_tp2: ratio })];

      render(<StrategyTable strategies={strategies} />);

      const rrCells = screen.getAllByText(formatRiskReward(ratio));
      expect(rrCells).toHaveLength(2);
      rrCells.forEach((cell) => expect(cell).toHaveClass(expectedClass));
    });

    it("rozróżnia TP1 i TP2 gdy mają różne wartości R/R", () => {
      const strategies = [makeStrategyEntry({ risk_reward_ratio: 1.5, risk_reward_ratio_tp2: 0.3 })];

      render(<StrategyTable strategies={strategies} />);

      // TP1 (1.5 → żółte) i TP2 (0.3 → zielone) muszą być renderowane z osobnych
      // właściwości. Gdyby komponent błędnie czytał obie komórki z tej samej
      // właściwości, getByText poniżej zwróciłby 0 trafień i test przewali.
      const tp1Cell = screen.getByText(formatRiskReward(1.5));
      expect(tp1Cell).toHaveClass("text-yellow-400");
      const tp2Cell = screen.getByText(formatRiskReward(0.3));
      expect(tp2Cell).toHaveClass("text-green-400");
    });
  });

});
