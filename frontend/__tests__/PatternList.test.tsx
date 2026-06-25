import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PatternList from "@/components/Patterns/PatternList";
import type { PatternScannerResult } from "@/types";

const mockPatterns: PatternScannerResult[] = [
  {
    pattern_type: "Hammer",
    category: "candlestick",
    bullish: true,
    confidence: 0.85,
    timeframes: ["H1", "D1"],
    representative_pattern: {
      pattern_type: "Hammer",
      bullish: true,
      confidence: 0.85,
      description: "Bullish reversal pattern",
      location: "body",
      category: "candlestick",
      timeframe: "H1",
      detected_at_index: 10,
      detected_at_timestamp: "2023-11-14T22:13:20Z",
      relevance_score: 0.85,
      target_price: 1.2000,
      indication: "buy",
      reliability: 3,
      detailed_description: "Detailed description",
    },
  },
  {
    pattern_type: "Shooting Star",
    category: "candlestick",
    bullish: false,
    confidence: 0.75,
    timeframes: ["M15"],
    representative_pattern: {
      pattern_type: "Shooting Star",
      bullish: false,
      confidence: 0.75,
      description: "Bearish reversal pattern",
      location: "body",
      category: "candlestick",
      timeframe: "M15",
      detected_at_index: 5,
      detected_at_timestamp: "2023-11-14T22:13:20Z",
      relevance_score: 0.75,
      target_price: null,
      indication: "sell",
      reliability: 2,
      detailed_description: "",
    },
  },
];

describe("PatternList", () => {
  it("pusta lista wyświetla komunikat 'Nie wykryto formacji cenowych'", () => {
    render(<PatternList patterns={[]} currentTimeframe="H1" />);

    expect(screen.getByText("Nie wykryto formacji cenowych")).toBeInTheDocument();
  });

  it("lista formacji wyświetla wiersze z nazwami", () => {
    render(<PatternList patterns={mockPatterns} currentTimeframe="H1" />);

    expect(screen.getByText("Hammer")).toBeInTheDocument();
    expect(screen.getByText("Shooting Star")).toBeInTheDocument();
  });

  it("kliknięcie formacji otwiera modal", async () => {
    const user = userEvent.setup();
    const handlePatternClick = vi.fn();

    render(<PatternList patterns={mockPatterns} currentTimeframe="H1" onPatternClick={handlePatternClick} />);

    const hammerButton = screen.getByRole("button", { name: /Hammer/i });
    await user.click(hammerButton);

    expect(handlePatternClick).toHaveBeenCalled();
  });

  it("checkbox 'Pokaż tylko ★★+' filtruje po wiarygodności", async () => {
    const user = userEvent.setup();

    render(<PatternList patterns={mockPatterns} currentTimeframe="H1" />);

    // Initially showReliableOnly=true, so only Hammer (reliability 3) is visible
    // Shooting Star has reliability 2, which is >= MIN_RELIABILITY_FILTER (2), so it should also be visible
    expect(screen.getByText("Hammer")).toBeInTheDocument();
    expect(screen.getByText("Shooting Star")).toBeInTheDocument();

    // Click the checkbox to disable the filter (show all patterns)
    const checkbox = screen.getByRole("checkbox", { name: "Pokaż tylko ★★+" });
    await user.click(checkbox);

    // Both patterns should still be visible (Shooting Star has reliability 2, meets threshold)
    expect(screen.getByText("Hammer")).toBeInTheDocument();
    expect(screen.getByText("Shooting Star")).toBeInTheDocument();
  });

  it("przycisk 'Pokaż wszystkie' rozwija pełną listę", async () => {
    const user = userEvent.setup();

    // Create more patterns to trigger "show more" button
    const manyPatterns: PatternScannerResult[] = Array.from({ length: 10 }, (_, i) => ({
      ...mockPatterns[0],
      pattern_type: `Pattern ${i + 1}`,
      representative_pattern: {
        ...mockPatterns[0].representative_pattern,
        pattern_type: `Pattern ${i + 1}`,
      },
    }));

    render(<PatternList patterns={manyPatterns} currentTimeframe="H1" />);

    // Initially only TOP_N (5) patterns are visible
    expect(screen.getByText("Pattern 1")).toBeInTheDocument();
    expect(screen.getByText("Pattern 5")).toBeInTheDocument();

    // Click "Pokaż wszystkie" button
    const showAllButton = screen.getByRole("button", { name: /Pokaż wszystkie/i });
    await user.click(showAllButton);

    // All patterns should now be visible
    expect(screen.getByText("Pattern 10")).toBeInTheDocument();
  });
});