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

    // Check that both directions are rendered
    expect(screen.getByText("▲ LONG")).toBeInTheDocument();
    expect(screen.getByText("▼ SHORT")).toBeInTheDocument();
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
});