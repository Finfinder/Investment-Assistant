"use client";

import { useState } from "react";
import type { Timeframe, IndicatorPreset } from "@/types";

export const POPULAR_INSTRUMENTS = [
  // Forex majors
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "AUDUSD",
  "USDCAD",
  "NZDUSD",
  "EURGBP",
  "EURJPY",
  "GBPJPY",
  // Forex cross pairs
  "AUDCAD",
  "AUDCHF",
  "AUDJPY",
  "CADJPY",
  "CHFJPY",
  "EURCHF",
  "EURAUD",
  "EURCAD",
  "GBPCAD",
  "GBPCHF",
  "AUDNZD",
  "NZDJPY",
  "NZDCAD",
  "NZDCHF",
  "EURNZD",
  "GBPNZD",
  // PLN pairs
  "AUDPLN",
  "CADPLN",
  "CHFPLN",
  "EURPLN",
  "GBPPLN",
  "JPYPLN",
  "USDPLN",
  // Commodities
  "GOLD",
  "SILVER",
  "XAUUSD",
  "XAGUSD",
  "OIL",
  "OILWTI",
  "BRENT",
  "NATGAS",
  "COFFEE",
  "COPPER",
  "PLATINUM",
  // Indices
  "US500",
  "US30",
  "US100",
  "DE40",
  "FR40",
  "UK100",
  "JP225",
  "W20",
];

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "M15", label: "M15 (15 min)" },
  { value: "H1", label: "H1 (1 godz)" },
  { value: "H4", label: "H4 (4 godz)" },
  { value: "D1", label: "D1 (1 dzień)" },
];

const PRESETS: { value: IndicatorPreset; label: string }[] = [
  { value: "investing", label: "Investing.com" },
  { value: "tradingview", label: "TradingView" },
];

interface AnalysisFormProps {
  onSubmit: (symbol: string, timeframe: Timeframe, preset: IndicatorPreset) => void | Promise<void>;
  isLoading: boolean;
}

export default function AnalysisForm({ onSubmit, isLoading }: Readonly<AnalysisFormProps>) {
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("H1");
  const [preset, setPreset] = useState<IndicatorPreset>("investing");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [error, setError] = useState("");
  const suggestionsId = "symbol-suggestions";

  function handleSymbolChange(value: string) {
    const upper = value.toUpperCase().replaceAll(/[^A-Z0-9/-]/g, "");
    setSymbol(upper);
    setError("");
    if (upper.length >= 1) {
      const filtered = POPULAR_INSTRUMENTS.filter((s) => s.startsWith(upper));
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0 && !isLoading);
      setActiveIndex(filtered.length > 0 ? 0 : -1);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
      setActiveIndex(-1);
    }
  }

  function selectSuggestion(value: string) {
    setSymbol(value);
    setSuggestions([]);
    setShowSuggestions(false);
    setActiveIndex(-1);
    setError("");
  }

  function handleSymbolFocus() {
    if (!isLoading && suggestions.length > 0) {
      setShowSuggestions(true);
      setActiveIndex((prev) => (prev >= 0 ? prev : 0));
    }
  }

  function handleSymbolBlur() {
    setShowSuggestions(false);
    setActiveIndex(-1);
  }

  function handleSymbolKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === "Escape") {
        setShowSuggestions(false);
        setActiveIndex(-1);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1));
      return;
    }

    if (e.key === "Enter") {
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        e.preventDefault();
        selectSuggestion(suggestions[activeIndex]);
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setShowSuggestions(false);
      setActiveIndex(-1);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) {
      setError("Symbol jest wymagany");
      return;
    }
    if (symbol.trim().length < 2) {
      setError("Symbol musi mieć co najmniej 2 znaki");
      return;
    }
    void onSubmit(symbol.trim(), timeframe, preset);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <div className="relative flex-1">
        <label htmlFor="symbol" className="mb-1 block text-sm font-medium text-muted">
          Symbol instrumentu
        </label>
        <input
          id="symbol"
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showSuggestions && suggestions.length > 0}
          aria-controls={suggestionsId}
          value={symbol}
          onChange={(e) => handleSymbolChange(e.target.value)}
          onFocus={handleSymbolFocus}
          onBlur={handleSymbolBlur}
          onKeyDown={handleSymbolKeyDown}
          placeholder="np. EURUSD, GOLD, US500"
          disabled={isLoading}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          autoComplete="off"
        />
        {showSuggestions && suggestions.length > 0 && (
          <div
            id={suggestionsId}
            className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-border bg-card p-1 shadow-lg"
          >
            {suggestions.map((s, index) => (
              <button
                key={s}
                type="button"
                tabIndex={-1}
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectSuggestion(s);
                }}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  activeIndex === index ? "bg-accent text-white" : "text-foreground hover:bg-border"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {error && <p className="mt-1 text-sm text-danger">{error}</p>}
      </div>

      <div>
        <label htmlFor="preset" className="mb-1 block text-sm font-medium text-muted">
          Preset wskaźników
        </label>
        <select
          id="preset"
          value={preset}
          onChange={(e) => setPreset(e.target.value as IndicatorPreset)}
          disabled={isLoading}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 sm:w-44"
        >
          {PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="timeframe" className="mb-1 block text-sm font-medium text-muted">
          Timeframe
        </label>
        <select
          id="timeframe"
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value as Timeframe)}
          disabled={isLoading}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 sm:w-44"
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf.value} value={tf.value}>
              {tf.label}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="rounded-lg bg-accent px-6 py-2.5 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            <span>Analizuję...</span>
          </span>
        ) : (
          "Analizuj"
        )}
      </button>
    </form>
  );
}
