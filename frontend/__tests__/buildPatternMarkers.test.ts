import { describe, it, expect } from "vitest";
import { buildPatternMarkers } from "@/components/Chart/CandlestickChart";
import type { UTCTimestamp } from "lightweight-charts";
import type { PatternDetection } from "@/types";

const TS1 = 1700000000 as UTCTimestamp;
const TS2 = 1700003600 as UTCTimestamp;

function makePattern({ pattern_type, bullish, ...overrides }: Partial<PatternDetection> & { pattern_type: string; bullish: boolean }): PatternDetection {
  return {
    pattern_type,
    bullish,
    confidence: 0.8,
    description: "",
    location: "body",
    category: "candlestick",
    timeframe: null,
    detected_at_index: null,
    detected_at_timestamp: "2023-11-14T22:13:20Z",
    relevance_score: 0.8,
    target_price: null,
    indication: "buy",
    reliability: 1,
    detailed_description: "",
    ...overrides,
  };
}

describe("buildPatternMarkers", () => {
  it("pojedyncza formacja → 1 marker z oryginalną nazwą", () => {
    const patterns = [makePattern({ pattern_type: "Hammer", bullish: true, detected_at_timestamp: "2023-11-14T22:13:20Z" })];
    const markers = buildPatternMarkers(patterns, TS1, null);

    expect(markers).toHaveLength(1);
    expect(markers[0].text).toBe("Hammer");
    expect(markers[0].color).toBe("#22c55e");
    expect(markers[0].position).toBe("belowBar");
    expect(markers[0].shape).toBe("arrowUp");
  });

  it("2 bullish formacje na tym samym timestamp → 1 zielony marker z łączoną nazwą", () => {
    const ts = "2023-11-14T22:13:20Z";
    const patterns = [
      makePattern({ pattern_type: "Hammer", bullish: true, detected_at_timestamp: ts }),
      makePattern({ pattern_type: "Morning Star", bullish: true, detected_at_timestamp: ts }),
    ];
    const markers = buildPatternMarkers(patterns, TS1, null);

    expect(markers).toHaveLength(1);
    expect(markers[0].text).toBe("Hammer / Morning Star");
    expect(markers[0].color).toBe("#22c55e");
    expect(markers[0].position).toBe("belowBar");
    expect(markers[0].shape).toBe("arrowUp");
  });

  it("2 bearish formacje na tym samym timestamp → 1 czerwony marker", () => {
    const ts = "2023-11-14T22:13:20Z";
    const patterns = [
      makePattern({ pattern_type: "Shooting Star", bullish: false, detected_at_timestamp: ts }),
      makePattern({ pattern_type: "Bearish Engulfing", bullish: false, detected_at_timestamp: ts }),
    ];
    const markers = buildPatternMarkers(patterns, TS1, null);

    expect(markers).toHaveLength(1);
    expect(markers[0].color).toBe("#ef4444");
    expect(markers[0].position).toBe("aboveBar");
    expect(markers[0].shape).toBe("arrowDown");
  });

  it("mix bullish + bearish na tym samym timestamp → 1 szary marker, pozycja aboveBar", () => {
    const ts = "2023-11-14T22:13:20Z";
    const patterns = [
      makePattern({ pattern_type: "Hammer", bullish: true, detected_at_timestamp: ts }),
      makePattern({ pattern_type: "Shooting Star", bullish: false, detected_at_timestamp: ts }),
    ];
    const markers = buildPatternMarkers(patterns, TS1, null);

    expect(markers).toHaveLength(1);
    expect(markers[0].color).toBe("#94a3b8");
    expect(markers[0].position).toBe("aboveBar");
  });

  it("highlight jednej formacji z grupy → marker żółty", () => {
    const ts = "2023-11-14T22:13:20Z";
    const hammer = makePattern({ pattern_type: "Hammer", bullish: true, detected_at_timestamp: ts });
    const doji = makePattern({ pattern_type: "Doji", bullish: true, detected_at_timestamp: ts });
    const markers = buildPatternMarkers([hammer, doji], TS1, hammer);

    expect(markers).toHaveLength(1);
    expect(markers[0].color).toBe("#eab308");
  });

  it("różne timestampy → osobne markery (brak grupowania)", () => {
    const patterns = [
      makePattern({ pattern_type: "Hammer", bullish: true, detected_at_timestamp: "2023-11-14T22:13:20Z" }),
      makePattern({ pattern_type: "Doji", bullish: true, detected_at_timestamp: "2023-11-14T23:13:20Z" }),
    ];
    const markers = buildPatternMarkers(patterns, TS2, null);

    expect(markers).toHaveLength(2);
    expect(markers.find((m) => m.text === "Hammer")).toBeDefined();
    expect(markers.find((m) => m.text === "Doji")).toBeDefined();
  });
});
