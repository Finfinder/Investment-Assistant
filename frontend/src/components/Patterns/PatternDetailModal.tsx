"use client";

import { useEffect, useRef } from "react";
import type { PatternScannerResult } from "@/types";

interface PatternDetailModalProps {
  pattern: PatternScannerResult | null;
  onClose: () => void;
}

const RELIABILITY_STARS: Record<number, string> = {
  1: "★",
  2: "★★",
  3: "★★★",
};

export default function PatternDetailModal({
  pattern,
  onClose,
}: Readonly<PatternDetailModalProps>) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (!pattern) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault()
      onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    dialogRef.current?.focus();

    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [pattern, onClose]);

  if (!pattern) return null;

  const representative = pattern.representative_pattern;
  const reliability = representative.reliability ?? 1;
  const stars = RELIABILITY_STARS[reliability] ?? "★";
  const confidencePct = Math.round(pattern.confidence * 100);
  const directionLabel = pattern.bullish ? "Bycza" : "Niedźwiedzia";
  const directionClass = pattern.bullish
    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
    : "bg-red-500/20 text-red-400 border border-red-500/40";
  let confidenceBarClass = "bg-red-500";
  if (pattern.confidence >= 0.8) {
    confidenceBarClass = "bg-emerald-500";
  } else if (pattern.confidence >= 0.6) {
    confidenceBarClass = "bg-yellow-500";
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <button
        type="button"
        aria-label="Zamknij szczegóły formacji"
        className="absolute inset-0"
        onClick={onClose}
      />
      <dialog
        ref={dialogRef}
        open
        aria-label={`Szczegóły formacji: ${pattern.pattern_type}`}
        tabIndex={-1}
        className="relative z-10 m-0 w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl outline-none backdrop:bg-transparent"
        onClose={onClose}
      >
        {/* Przycisk zamknięcia */}
        <button
          type="button"
          aria-label="Zamknij"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
        >
          ✕
        </button>

        {/* Nagłówek */}
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground">{pattern.pattern_type}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${directionClass}`}>
              {directionLabel}
            </span>
            <span
              className="text-sm text-amber-400"
              title={`Wiarygodność: ${reliability}/3`}
              aria-label={`Wiarygodność ${reliability} z 3`}
            >
              {stars}
            </span>
          </div>
        </div>

        {/* Wskazanie */}
        {representative.indication && (
          <div className="mb-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Wskazanie
            </p>
            <p className="mt-0.5 text-sm font-medium text-foreground">{representative.indication}</p>
          </div>
        )}

        <div className="mb-4 grid gap-3 rounded-lg border border-border/70 bg-background/40 p-3 text-sm">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Interwał reprezentatywny</p>
            <p className="mt-1 text-foreground">{representative.timeframe ?? "Brak"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Ramy czasowe</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {pattern.timeframes.map((timeframe) => (
                <span key={timeframe} className="rounded-full border border-border px-2 py-1 text-xs text-foreground">
                  {timeframe}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Szczegółowy opis */}
        {representative.detailed_description && (
          <div className="mb-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Opis formacji
            </p>
            <p className="mt-0.5 text-sm leading-relaxed text-foreground">
              {representative.detailed_description}
            </p>
          </div>
        )}

        {/* Pasek pewności */}
        <div className="mb-4">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Pewność sygnału
            </p>
            <span className="text-xs font-semibold text-foreground">{confidencePct}%</span>
          </div>
          <progress
            value={confidencePct}
            max={100}
            className="sr-only"
            aria-label={`Pewność sygnału: ${confidencePct}%`}
          >
            {confidencePct}%
          </progress>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              aria-hidden="true"
              className={`h-full rounded-full transition-all ${confidenceBarClass}`}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
        </div>

        {/* Lokalizacja */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            {representative.location === "emerging" ? "Formacja wyłaniająca się" : "Formacja zakończona"}
          </p>
          {representative.detected_at_index !== null && (
            <p className="text-xs text-muted-foreground">
              Indeks świecy: {representative.detected_at_index}
            </p>
          )}
        </div>
      </dialog>
    </div>
  );
}
