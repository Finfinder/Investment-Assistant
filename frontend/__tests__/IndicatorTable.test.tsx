import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MovingAverageTable from "@/components/IndicatorTable/MovingAverageTable";
import OscillatorTable from "@/components/IndicatorTable/OscillatorTable";
import type { MovingAverage, IndicatorValue } from "@/types";

describe("MovingAverageTable", () => {
  it("z pustą listą zwraca null (nic nie renderuje)", () => {
    const { container } = render(<MovingAverageTable movingAverages={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("z danymi wyświetla okresy, wartości SMA/EMA, sygnały", () => {
    const movingAverages: MovingAverage[] = [
      {
        period: 50,
        sma_value: 1.1234,
        sma_signal: "buy",
        ema_value: 1.1245,
        ema_signal: "neutral",
      },
      {
        period: 200,
        sma_value: 1.0987,
        sma_signal: "sell",
        ema_value: 1.0998,
        ema_signal: "strong_buy",
      },
    ];

    render(<MovingAverageTable movingAverages={movingAverages} />);

    expect(screen.getByRole("heading", { name: "Średnie kroczące" })).toBeInTheDocument();
    expect(screen.getByText("MA(50)")).toBeInTheDocument();
    expect(screen.getByText("MA(200)")).toBeInTheDocument();
    expect(screen.getByText("1.1234")).toBeInTheDocument();
    expect(screen.getByText("1.1245")).toBeInTheDocument();
    expect(screen.getByText("Kup")).toBeInTheDocument();
    expect(screen.getByText("Sprzedaj")).toBeInTheDocument();
    expect(screen.getByText("Mocne Kup")).toBeInTheDocument();
  });
});

describe("OscillatorTable", () => {
  it("z pustą listą zwraca null (nic nie renderuje)", () => {
    const { container } = render(<OscillatorTable indicators={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("z danymi wyświetla nazwy, wartości, sygnały", () => {
    const indicators: IndicatorValue[] = [
      { name: "RSI", value: 65.5, signal: "buy" },
      { name: "MACD", value: -0.0012, signal: "sell" },
    ];

    render(<OscillatorTable indicators={indicators} />);

    expect(screen.getByRole("heading", { name: "Oscylatory" })).toBeInTheDocument();
    expect(screen.getByText("RSI")).toBeInTheDocument();
    expect(screen.getByText("MACD")).toBeInTheDocument();
    // formatValue formats 65.5 as 65.5000 (4 decimal places)
    expect(screen.getByText("65.5000")).toBeInTheDocument();
    // formatValue formats -0.0012 as -0.0012 (4 decimal places)
    expect(screen.getByText("-0.0012")).toBeInTheDocument();
    expect(screen.getByText("Kup")).toBeInTheDocument();
    expect(screen.getByText("Sprzedaj")).toBeInTheDocument();
  });
});

describe("formatValue helper", () => {
  it("formatuje liczby całkowite bez miejsc po przecinku", () => {
    render(<OscillatorTable indicators={[{ name: "Test", value: 100, signal: "neutral" }]} />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("formatuje liczby dziesiętne z 4 miejscami", () => {
    render(<OscillatorTable indicators={[{ name: "Test", value: 1.2345, signal: "neutral" }]} />);
    expect(screen.getByText("1.2345")).toBeInTheDocument();
  });

  it("wyświetla — dla null/undefined", () => {
    render(<OscillatorTable indicators={[{ name: "Test", value: null, signal: "neutral" }]} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});