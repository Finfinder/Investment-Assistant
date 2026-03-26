"use client";

import { useState, useRef, useEffect } from "react";
import type { Timeframe } from "@/types";

const POPULAR_INSTRUMENTS = [
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
  "GOLD",
  "SILVER",
  "XAUUSD",
  "XAGUSD",
  "OIL",
  "USOIL",
  "BRENT",
  "US500",
  "US30",
  "US100",
  "DE40",
  "UK100",
  "JP225",
  "NATGAS",
];

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "M15", label: "M15 (15 min)" },
  { value: "H1", label: "H1 (1 godz)" },
  { value: "H4", label: "H4 (4 godz)" },
  { value: "D1", label: "D1 (1 dzień)" },
];

interface AnalysisFormProps {
  onSubmit: (symbol: string, timeframe: Timeframe) => void;
  isLoading: boolean;
}

export default function AnalysisForm({ onSubmit, isLoading }: Readonly<AnalysisFormProps>) {
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("H1");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSymbolChange(value: string) {
    const upper = value.toUpperCase().replaceAll(/[^A-Z0-9/-]/g, "");
    setSymbol(upper);
    setError("");
    if (upper.length >= 1) {
      const filtered = POPULAR_INSTRUMENTS.filter((s) => s.startsWith(upper));
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }

  function selectSuggestion(s: string) {
    setSymbol(s);
    setShowSuggestions(false);
    inputRef.current?.focus();
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
    onSubmit(symbol.trim(), timeframe);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <div className="relative flex-1">
        <label htmlFor="symbol" className="mb-1 block text-sm font-medium text-muted">
          Symbol instrumentu
        </label>
        <input
          ref={inputRef}
          id="symbol"
          type="text"
          value={symbol}
          onChange={(e) => handleSymbolChange(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setShowSuggestions(true);
          }}
          placeholder="np. EURUSD, GOLD, US500"
          disabled={isLoading}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          autoComplete="off"
        />
        {showSuggestions && (
          <ul
            ref={suggestionsRef}
            className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-border bg-card shadow-lg"
          >
            {suggestions.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => selectSuggestion(s)}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-border"
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && <p className="mt-1 text-sm text-danger">{error}</p>}
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
        className="rounded-lg bg-accent px-6 py-2.5 font-medium text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Analizuję...
          </span>
        ) : (
          "Analizuj"
        )}
      </button>
    </form>
  );
}
