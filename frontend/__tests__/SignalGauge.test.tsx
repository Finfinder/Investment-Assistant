import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import SignalGauge from "@/components/SignalSummary/SignalGauge";
import type { SignalType } from "@/types";

describe("SignalGauge", () => {
  afterEach(() => {
    cleanup();
  });

  it("renderuje etykietę (label)", () => {
    render(
      <SignalGauge
        label="Test Gauge"
        signal="neutral"
        buyCount={0}
        sellCount={0}
        neutralCount={0}
      />,
    );

    expect(screen.getByText("Test Gauge")).toBeInTheDocument();
  });

  it.each([
    ["strong_buy", "Mocne Kup"],
    ["buy", "Kup"],
    ["neutral", "Neutralny"],
    ["sell", "Sprzedaj"],
    ["strong_sell", "Mocne Sprzedaj"],
  ] as const)("wyświetla etykietę sygnału '%s'", (signal, expectedLabel) => {
    render(
      <SignalGauge
        label="Test Gauge"
        signal={signal}
        buyCount={0}
        sellCount={0}
        neutralCount={0}
      />,
    );

    // Use getAllByText to avoid conflicts with other text in the component
    const labelElements = screen.getAllByText(expectedLabel);
    expect(labelElements.length).toBeGreaterThan(0);
  });

  it("wyświetla liczniki buy/sell/neutral gdy total > 0", () => {
    render(
      <SignalGauge
        label="Test Gauge"
        signal="buy"
        buyCount={5}
        sellCount={2}
        neutralCount={3}
      />,
    );

    expect(screen.getByText("Kup: 5")).toBeInTheDocument();
    expect(screen.getByText("Sprzedaj: 2")).toBeInTheDocument();
    expect(screen.getByText("Neutralny: 3")).toBeInTheDocument();
  });

  it("nie wyświetla liczników gdy total = 0", () => {
    render(
      <SignalGauge
        label="Test Gauge"
        signal="neutral"
        buyCount={0}
        sellCount={0}
        neutralCount={0}
      />,
    );

    // The counts section (with "Kup:", "Sprzedaj:", "Neutralny:" labels) is not rendered when total is 0
    // Note: "Neutralny" appears in static labels, so we check for the count format specifically
    expect(screen.queryByText("Kup: 0")).not.toBeInTheDocument();
    expect(screen.queryByText("Sprzedaj: 0")).not.toBeInTheDocument();
    expect(screen.queryByText("Neutralny: 0")).not.toBeInTheDocument();
  });

  it("ma poprawny aria-label w elemencie meter", () => {
    render(
      <SignalGauge
        label="Test Gauge"
        signal="buy"
        buyCount={1}
        sellCount={0}
        neutralCount={0}
      />,
    );

    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-label", "Test Gauge: Kup");
  });
});