import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PatternDetailModal from "@/components/Patterns/PatternDetailModal";
import type { PatternScannerResult } from "@/types";

function makePatternScannerResult(overrides: Partial<PatternScannerResult> = {}): PatternScannerResult {
  return {
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
      target_price: 1.2,
      indication: "buy",
      reliability: 3,
      detailed_description: "Detailed description of hammer pattern",
    },
    ...overrides,
  };
}

describe("PatternDetailModal", () => {
  it("nie renderuje się gdy pattern jest null", () => {
    const { container } = render(
      <PatternDetailModal pattern={null} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renderuje się gdy pattern jest non-null", () => {
    render(
      <PatternDetailModal pattern={makePatternScannerResult()} onClose={vi.fn()} />
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Hammer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Zamknij$/i })).toBeInTheDocument();
  });

  it("zamyka modal przyciskiem X", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <PatternDetailModal pattern={makePatternScannerResult()} onClose={handleClose} />
    );
    await user.click(screen.getByRole("button", { name: /Zamknij$/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("zamyka modal klawiszem Escape", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <PatternDetailModal pattern={makePatternScannerResult()} onClose={handleClose} />
    );
    await user.keyboard("{Escape}");
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("zamyka modal przyciskiem tła", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <PatternDetailModal pattern={makePatternScannerResult()} onClose={handleClose} />
    );
    await user.click(screen.getByRole("button", { name: /Zamknij szczegóły formacji/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renderuje podstawowe pola formacji", () => {
    const pattern = makePatternScannerResult({ timeframes: ["D1"] });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);

    expect(screen.getByText(pattern.pattern_type)).toBeInTheDocument();
    expect(screen.getByText(/Bycza/i)).toBeInTheDocument();
    expect(screen.getByText("★★★")).toBeInTheDocument();
    expect(screen.getByText(pattern.representative_pattern.indication)).toBeInTheDocument();
    expect(screen.getByText(pattern.representative_pattern.timeframe!)).toBeInTheDocument();
    pattern.timeframes.forEach((tf) => {
      expect(screen.getByText(tf)).toBeInTheDocument();
    });
    expect(screen.getByText(pattern.representative_pattern.detailed_description)).toBeInTheDocument();
    expect(screen.getByText(/Pewność sygnału/)).toBeInTheDocument();
    expect(screen.getByText(/Formacja zakończona/i)).toBeInTheDocument();
    expect(screen.getByText(`Indeks świecy: ${pattern.representative_pattern.detected_at_index}`)).toBeInTheDocument();
  });

  it("renderuje pola dla formacji niedźwiedziego", () => {
    const pattern = makePatternScannerResult({ 
      bullish: false,
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        bullish: false,
        indication: "sell"
      }
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);

    expect(screen.getByText(/Niedźwiedzia/i)).toBeInTheDocument();
    expect(screen.getByText(pattern.representative_pattern.indication)).toBeInTheDocument();
  });

  it("renderuje formację wyłaniającą się gdy location jest 'emerging'", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        location: "emerging"
      }
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);

    expect(screen.getByText(/Formacja wyłaniająca się/i)).toBeInTheDocument();
  });

  it("renderuje procent pewności sygnału", () => {
    const pattern = makePatternScannerResult({ confidence: 0.75 });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);

    const progressBar = screen.getByRole("progressbar", { name: /Pewność sygnału/ });
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute("value", "75");
    
    // Find only visible text element
    const visibleElements = screen.getAllByText(/75%/).filter(el => el.classList.contains('text-foreground'));
    expect(visibleElements.length).toBeGreaterThan(0);
  });

  it.each([
    { reliability: 1, stars: "★" },
    { reliability: 2, stars: "★★" },
    { reliability: 3, stars: "★★★" },
    { reliability: undefined, stars: "★" },
  ])("renderuje $stars gwiazdek dla reliability = $reliability", ({ reliability, stars }) => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        reliability: reliability as number,
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    expect(screen.getByText(stars)).toBeInTheDocument();
  });

  it.each([
    { confidence: 0.5, className: "bg-red-500" },
    { confidence: 0.65, className: "bg-yellow-500" },
    { confidence: 0.8, className: "bg-emerald-500" },
  ])("ma pasek pewności koloru $className dla confidence = $confidence", ({ confidence, className }) => {
    const pattern = makePatternScannerResult({ confidence });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    const progressBar = document.querySelector('.rounded-full[aria-hidden="true"]');
    expect(progressBar).toHaveClass(className);
  });

  it("nie renderuje sekcji Opis formacji gdy detailed_description jest puste", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        detailed_description: "",
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    expect(screen.queryByText(/Opis formacji/i)).not.toBeInTheDocument();
  });

  it("nie renderuje sekcji Wskazanie gdy indication jest puste", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        indication: "",
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    expect(screen.queryByText(/Wskazanie/i)).not.toBeInTheDocument();
  });

  it("wyświetla 'Brak' w Interwał reprezentatywny gdy timeframe jest null", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        timeframe: null,
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    expect(screen.getByText("Brak")).toBeInTheDocument();
  });

  it("nie renderuje Indeks świecy gdy detected_at_index jest null", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        detected_at_index: null,
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    expect(screen.queryByText(/Indeks świecy/i)).not.toBeInTheDocument();
  });

  it("renderuje cel cenowy gdy target_price jest dostępny", () => {
    const targetPrice = 1.2345;
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        target_price: targetPrice,
      },
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    
    // Check if target price is displayed (implement this test once the component renders target price)
    // expect(screen.getByText(targetPrice.toString())).toBeInTheDocument();
  });

  it("renderuje kategorię formacji", () => {
    const pattern = makePatternScannerResult({ category: "chart_pattern" });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    
    // Check if category is displayed (implement this test once the component renders category)
    // expect(screen.getByText(pattern.category)).toBeInTheDocument();
  });

  it("renderuje lokalizację formacji", () => {
    const pattern = makePatternScannerResult({
      representative_pattern: {
        ...makePatternScannerResult().representative_pattern,
        location: "emerging"
      }
    });
    render(<PatternDetailModal pattern={pattern} onClose={vi.fn()} />);
    
    expect(screen.getByText(/Formacja wyłaniająca się/i)).toBeInTheDocument();
  });
});
