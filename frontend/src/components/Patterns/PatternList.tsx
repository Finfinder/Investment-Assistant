"use client";

import { useState } from "react";
import type { PatternCategory, PatternDetection } from "@/types";
import { confidenceBarClass } from "@/lib/format";
import PatternDetailModal from "./PatternDetailModal";

interface PatternListProps {
  patterns: PatternDetection[];
  totalCandles?: number;
  onPatternClick?: (pattern: PatternDetection) => void;
}

const CATEGORY_LABELS: Record<PatternCategory | "all", string> = {
  all: "Wszystkie",
  candlestick: "Świecowe",
  chart_pattern: "Wykresowe",
  support_resistance: "S/R",
  fibonacci: "Fibonacci",
  iki: "IKI",
};

const CATEGORY_ORDER: Array<PatternCategory | "all"> = [
  "all",
  "candlestick",
  "chart_pattern",
  "support_resistance",
  "fibonacci",
  "iki",
];

const TOP_N = 5;

const RELIABILITY_STARS: Record<number, string> = {
  1: "★",
  2: "★★",
  3: "★★★",
};

export default function PatternList({ patterns, totalCandles, onPatternClick }: Readonly<PatternListProps>) {
  const [activeCategory, setActiveCategory] = useState<PatternCategory | "all">("all");
  const [expanded, setExpanded] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState<PatternDetection | null>(null);

  if (patterns.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center text-muted">
        Nie wykryto formacji cenowych
      </div>
    );
  }

  // Wzorce posortowane są już po relevance_score malejąco (z backendu)
  const filtered =
    activeCategory === "all" ? patterns : patterns.filter((p) => p.category === activeCategory);

  const visible = expanded ? filtered : filtered.slice(0, TOP_N);
  const hasMore = filtered.length > TOP_N;

  const categoriesPresent = new Set(patterns.map((p) => p.category));
  const visibleTabs = CATEGORY_ORDER.filter(
    (c) => c === "all" || categoriesPresent.has(c)
  );

  const handlePatternClick = (pattern: PatternDetection) => {
    setSelectedPattern(pattern);
    onPatternClick?.(pattern);
  };

  return (
    <>
      <div className="rounded-xl border border-border bg-card">
        <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Formacje cenowe</h3>

        {/* Zakładki kategorii */}
        <div className="flex gap-1 overflow-x-auto border-b border-border px-3 py-2">
          {visibleTabs.map((cat) => {
            const count = cat === "all" ? patterns.length : patterns.filter((p) => p.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => {
                  setActiveCategory(cat);
                  setExpanded(false);
                }}
                className={`shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? "bg-primary text-primary-foreground"
                    : "text-muted hover:bg-border/40"
                }`}
              >
                {CATEGORY_LABELS[cat]} ({count})
              </button>
            );
          })}
        </div>

        {/* Lista formacji */}
        <div className="divide-y divide-border/50">
          {visible.length === 0 ? (
            <p className="px-4 py-3 text-sm text-muted">Brak formacji w tej kategorii</p>
          ) : (
            visible.map((pattern, i) => (
              <PatternRow
                key={`${pattern.pattern_type}-${i}`}
                pattern={pattern}
                totalCandles={totalCandles}
                onPatternClick={handlePatternClick}
              />
            ))
          )}
        </div>

        {/* Rozwiń / Zwiń */}
        {hasMore && (
          <div className="border-t border-border px-4 py-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-muted transition-colors hover:text-foreground"
            >
              {expanded ? "Zwiń ▲" : `Pokaż wszystkie (${filtered.length}) ▼`}
            </button>
          </div>
        )}
      </div>

      <PatternDetailModal
        pattern={selectedPattern}
        onClose={() => setSelectedPattern(null)}
      />
    </>
  );
}

interface PatternRowProps {
  pattern: PatternDetection;
  totalCandles?: number;
  onPatternClick?: (pattern: PatternDetection) => void;
}

function PatternRow({ pattern, totalCandles, onPatternClick }: Readonly<PatternRowProps>) {
  const candlesAgo =
    totalCandles !== undefined && pattern.detected_at_index !== null
      ? totalCandles - 1 - pattern.detected_at_index
      : null;

  const isStale = candlesAgo !== null && candlesAgo > 20;
  const reliability = pattern.reliability ?? 1;
  const stars = RELIABILITY_STARS[reliability];

  return (
    <button
      onClick={() => onPatternClick?.(pattern)}
      className="flex w-full items-start gap-4 px-4 py-3 text-left transition-colors hover:bg-border/20"
    >
      {/* Ikona */}
      <span className="mt-0.5 text-xl">{pattern.bullish ? "📈" : "📉"}</span>

      {/* Treść */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`font-medium ${isStale ? "text-muted" : ""}`}>{pattern.pattern_type}</span>
          <span
            className={`rounded px-1.5 py-0.5 text-xs font-medium ${
              pattern.bullish ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"
            }`}
          >
            {pattern.bullish ? "Bycza" : "Niedźwiedzia"}
          </span>
          {stars && (
            <span
              className="text-xs text-amber-400"
              title={`Wiarygodność: ${reliability}/3`}
              aria-label={`Wiarygodność ${reliability} z 3`}
            >
              {stars}
            </span>
          )}
          {candlesAgo !== null && (
            <span className={`text-xs ${isStale ? "text-red-400/70" : "text-muted"}`}>
              {candlesAgo === 0 ? "ostatnia świeca" : `${candlesAgo} świec temu`}
            </span>
          )}
        </div>
        {pattern.description && <p className="mt-1 text-sm text-muted">{pattern.description}</p>}
        {pattern.target_price !== null && pattern.target_price !== undefined && (
          <p className="mt-0.5 text-xs text-muted">
            Cel:{" "}
            <span className={pattern.bullish ? "text-green-400" : "text-red-400"}>
              {pattern.target_price.toFixed(4)}
            </span>
          </p>
        )}
      </div>

      {/* Słupek pewności */}
      <div className="w-20 shrink-0">
        <div className="mb-1 text-right text-xs text-muted">{Math.round(pattern.confidence * 100)}%</div>
        <div className="h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className={`h-full rounded-full ${confidenceBarClass(pattern.confidence * 100)}`}
            style={{ width: `${pattern.confidence * 100}%` }}
          />
        </div>
      </div>
    </button>
  );
}
