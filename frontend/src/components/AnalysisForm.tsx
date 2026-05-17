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
  onSubmit: (symbol: string, timeframe: Timeframe, preset: IndicatorPreset) => void;
  isLoading: boolean;
}

export default function AnalysisForm({ onSubmit, isLoading }: Readonly<AnalysisFormProps>) {
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("H1");
  const [preset, setPreset] = useState<IndicatorPreset>("investing");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState("");
  const listboxId = "symbol-suggestions";

  function handleSymbolChange(value: string) {
    const upper = value.toUpperCase().replaceAll(/[^A-Z0-9/-]/g, "");
    setSymbol(upper);
    setError("");
    if (upper.length >= 1) {
      setSuggestions(POPULAR_INSTRUMENTS.filter((s) => s.startsWith(upper)));
    } else {
      setSuggestions([]);
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
    onSubmit(symbol.trim(), timeframe, preset);
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
          list={listboxId}
          value={symbol}
          onChange={(e) => handleSymbolChange(e.target.value)}
          placeholder="np. EURUSD, GOLD, US500"
          disabled={isLoading}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          autoComplete="off"
        />
        <datalist id={listboxId}>
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
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
