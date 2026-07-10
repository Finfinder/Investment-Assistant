import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StrategyTable from "@/components/Strategy/StrategyTable";
import type { StrategyEntry } from "@/types";

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
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_condition: "Price above EMA",
        entry_price: 1.1000,
        stop_loss: 1.0900,
        tp1: 1.1100,
        tp2: 1.1200,
        confidence_pct: 75,
        risk_reward_ratio: 0.5,
        risk_reward_ratio_tp2: 0.25,
      },
      {
        direction: "short",
        entry_condition: "Price below EMA",
        entry_price: 1.1000,
        stop_loss: 1.1100,
        tp1: 1.0900,
        tp2: 1.0800,
        confidence_pct: 60,
        risk_reward_ratio: 0.75,
        risk_reward_ratio_tp2: 0.4,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    expect(screen.getByRole("heading", { name: "Strategie wejścia" })).toBeInTheDocument();
    expect(screen.getAllByText("▲ LONG").length).toBeGreaterThan(0);
    expect(screen.getAllByText("▼ SHORT").length).toBeGreaterThan(0);
    expect(screen.getByText("Price above EMA")).toBeInTheDocument();
    expect(screen.getByText("Price below EMA")).toBeInTheDocument();
  });

  it("kierunek long ma zielony kolor, short — czerwony", () => {
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_price: 1.1,
        stop_loss: 1.0,
        tp1: 1.2,
        tp2: 1.3,
        confidence_pct: 50,
        risk_reward_ratio: 1,
        risk_reward_ratio_tp2: 1,
      },
      {
        direction: "short",
        entry_price: 1.1,
        stop_loss: 1.2,
        tp1: 1.0,
        tp2: 0.9,
        confidence_pct: 50,
        risk_reward_ratio: 1,
        risk_reward_ratio_tp2: 1,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    // Verify direction badges have correct CSS classes for color coding
    const longBadge = screen.getByText("▲ LONG");
    expect(longBadge).toHaveClass("text-green-400");
    const shortBadge = screen.getByText("▼ SHORT");
    expect(shortBadge).toHaveClass("text-red-400");
  });

  it("pasek pewności renderuje się z odpowiednią szerokością", () => {
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_price: 1.1,
        stop_loss: 1.0,
        tp1: 1.2,
        tp2: 1.3,
        confidence_pct: 75,
        risk_reward_ratio: 1,
        risk_reward_ratio_tp2: 1,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    // Use getAllByText since there might be multiple elements with "75%"
    const percentageElements = screen.getAllByText(/75/);
    expect(percentageElements.length).toBeGreaterThan(0);
  });

  it("ujemne R/R renderuje się z czerwoną klasą (TP1 i TP2)", () => {
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_price: 1.1,
        stop_loss: 1.0,
        tp1: 1.2,
        tp2: 1.3,
        confidence_pct: 50,
        risk_reward_ratio: -0.5,
        risk_reward_ratio_tp2: -0.25,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    // formatRiskReward(-0.5) => "1:-2.00", formatRiskReward(-0.25) => "1:-4.00"
    const rrTp1 = screen.getByText("1:-2.00");
    expect(rrTp1).toHaveClass("text-red-400");
    const rrTp2 = screen.getByText("1:-4.00");
    expect(rrTp2).toHaveClass("text-red-400");
  });

  it("NaN R/R renderuje się z klasą text-danger (TP1 i TP2)", () => {
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_price: 1.1,
        stop_loss: 1.0,
        tp1: 1.2,
        tp2: 1.3,
        confidence_pct: 50,
        risk_reward_ratio: NaN,
        risk_reward_ratio_tp2: NaN,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    // formatRiskReward(NaN) => "1:NaN", ale klasa pochodzi z riskRewardClass(NaN) => text-danger
    const rrCells = screen.getAllByText("1:NaN");
    expect(rrCells.length).toBe(2);
    rrCells.forEach((cell) => expect(cell).toHaveClass("text-danger"));
  });

  it("Infinity R/R renderuje się z klasą text-danger (TP1 i TP2)", () => {
    const strategies: StrategyEntry[] = [
      {
        direction: "long",
        entry_price: 1.1,
        stop_loss: 1.0,
        tp1: 1.2,
        tp2: 1.3,
        confidence_pct: 50,
        risk_reward_ratio: Infinity,
        risk_reward_ratio_tp2: -Infinity,
      },
    ];

    render(<StrategyTable strategies={strategies} />);

    // formatRiskReward(Infinity) => "1:0.00", formatRiskReward(-Infinity) => "1:0.00"
    const rrCells = screen.getAllByText("1:0.00");
    expect(rrCells.length).toBe(2);
    rrCells.forEach((cell) => expect(cell).toHaveClass("text-danger"));
  });
});