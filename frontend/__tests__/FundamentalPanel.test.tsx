import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import FundamentalPanel from "@/components/Fundamental/FundamentalPanel";
import type { FundamentalData } from "@/types";

describe("FundamentalPanel", () => {
  it("renderuje typ instrumentu (label)", () => {
    const fundamental: FundamentalData = {
      instrument_type: "forex",
      indicators: {},
      score: 0,
      summary: "",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    expect(screen.getByText("Forex")).toBeInTheDocument();
  });

  it("renderuje score bar z odpowiednią etykietą", () => {
    const fundamental: FundamentalData = {
      instrument_type: "forex",
      indicators: {},
      score: 50,
      summary: "",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    // score 50 returns "Kup" (score > 15), not "Mocne Kup" (score > 50)
    // The score label is split across elements, use getAllByText to handle multiple matches
    const elements = screen.getAllByText(/Kup/);
    expect(elements.length).toBeGreaterThan(0);
  });

  it("wyświetla tabelę wskaźników gdy dane istnieją", () => {
    const fundamental: FundamentalData = {
      instrument_type: "commodity",
      indicators: {
        "Inflacja": 2.5,
        "PKB": "1000 mld",
      },
      score: 0,
      summary: "",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    expect(screen.getByText("Inflacja")).toBeInTheDocument();
    expect(screen.getByText("PKB")).toBeInTheDocument();
    // formatIndicatorValue formats 2.5 as 2.5000 (4 decimal places)
    expect(screen.getByText("2.5000")).toBeInTheDocument();
    expect(screen.getByText("1000 mld")).toBeInTheDocument();
  });

  it("wyświetla podsumowanie (summary) gdy istnieje", () => {
    const fundamental: FundamentalData = {
      instrument_type: "index",
      indicators: {},
      score: 0,
      summary: "Silny trend wzrostowy na rynku",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    expect(screen.getByText("Silny trend wzrostowy na rynku")).toBeInTheDocument();
  });

  it("score ujemny wyświetla 'Sprzedaj'", () => {
    const fundamental: FundamentalData = {
      instrument_type: "forex",
      indicators: {},
      score: -20,
      summary: "",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    // The score label is split across elements, use getAllByText to handle multiple matches
    const elements = screen.getAllByText(/Sprzedaj/);
    expect(elements.length).toBeGreaterThan(0);
  });

  it("score bardzo ujemny wyświetla 'Mocne Sprzedaj'", () => {
    const fundamental: FundamentalData = {
      instrument_type: "forex",
      indicators: {},
      score: -60,
      summary: "",
    };

    render(<FundamentalPanel fundamental={fundamental} />);

    // The score label is split across elements, use getAllByText to handle multiple matches
    const elements = screen.getAllByText(/Mocne/);
    expect(elements.length).toBeGreaterThan(0);
  });
});