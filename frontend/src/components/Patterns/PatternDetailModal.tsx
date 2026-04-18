"use client";

import { useEffect, useRef } from "react";
import type { PatternDetection } from "@/types";

interface PatternDetailModalProps {
  pattern: PatternDetection | null;
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
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pattern) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    dialogRef.current?.focus();
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [pattern, onClose]);

  if (!pattern) return null;

  const reliability = pattern.reliability ?? 1;
  const stars = RELIABILITY_STARS[reliability] ?? "★";
  const confidencePct = Math.round(pattern.confidence * 100);
  const directionLabel = pattern.bullish ? "Bycza" : "Niedźwiedzia";
  const directionClass = pattern.bullish
    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
    : "bg-red-500/20 text-red-400 border border-red-500/40";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      aria-hidden="false"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Szczegóły formacji: ${pattern.pattern_type}`}
        tabIndex={-1}
        className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Przycisk zamknięcia */}
        <button
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
        {pattern.indication && (
          <div className="mb-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Wskazanie
            </p>
            <p className="mt-0.5 text-sm font-medium text-foreground">{pattern.indication}</p>
          </div>
        )}

        {/* Szczegółowy opis */}
        {pattern.detailed_description && (
          <div className="mb-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Opis formacji
            </p>
            <p className="mt-0.5 text-sm leading-relaxed text-foreground">
              {pattern.detailed_description}
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
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={`h-full rounded-full transition-all ${
                pattern.confidence >= 0.8
                  ? "bg-emerald-500"
                  : pattern.confidence >= 0.6
                    ? "bg-yellow-500"
                    : "bg-red-500"
              }`}
              style={{ width: `${confidencePct}%` }}
              role="progressbar"
              aria-valuenow={confidencePct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Pewność sygnału: ${confidencePct}%`}
            />
          </div>
        </div>

        {/* Lokalizacja */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            {pattern.location === "emerging" ? "Formacja wyłaniająca się" : "Formacja zakończona"}
          </p>
          {pattern.detected_at_index !== null && (
            <p className="text-xs text-muted-foreground">
              Indeks świecy: {pattern.detected_at_index}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
