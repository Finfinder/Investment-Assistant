import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChartToolbar from "@/components/Chart/ChartToolbar";
import type { ChartLayerVisibility } from "@/types";

describe("ChartToolbar", () => {
  it("renderuje 4 przyciski warstw", () => {
    const visibility: ChartLayerVisibility = {
      ema: true,
      pivotPoints: false,
      fibonacci: false,
      patterns: true,
    };

    render(<ChartToolbar visibility={visibility} onChange={() => {}} />);

    expect(screen.getByRole("button", { name: "EMA" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pivot Points" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fibonacci" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Formacje" })).toBeInTheDocument();
  });

  it("aria-pressed odzwierciedla stan warstwy", () => {
    const visibility: ChartLayerVisibility = {
      ema: true,
      pivotPoints: false,
      fibonacci: true,
      patterns: false,
    };

    render(<ChartToolbar visibility={visibility} onChange={() => {}} />);

    expect(screen.getByRole("button", { name: "EMA" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Pivot Points" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Fibonacci" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Formacje" })).toHaveAttribute("aria-pressed", "false");
  });

  it("kliknięcie przycisku przełącza stan warstwy", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    const visibility: ChartLayerVisibility = {
      ema: true,
      pivotPoints: false,
      fibonacci: false,
      patterns: true,
    };

    render(<ChartToolbar visibility={visibility} onChange={handleChange} />);

    const emaButton = screen.getByRole("button", { name: "EMA" });
    await user.click(emaButton);

    expect(handleChange).toHaveBeenCalledWith({
      ema: false,
      pivotPoints: false,
      fibonacci: false,
      patterns: true,
    });
  });
});