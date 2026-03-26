import type { PatternDetection } from "@/types";
import { confidenceBarClass } from "@/lib/format";

interface PatternListProps {
  patterns: PatternDetection[];
  onPatternClick?: (patternType: string) => void;
}

export default function PatternList({ patterns, onPatternClick }: Readonly<PatternListProps>) {
  if (patterns.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center text-muted">
        Nie wykryto formacji cenowych
      </div>
    );
  }

  const sorted = [...patterns].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="rounded-xl border border-border bg-card">
      <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Formacje cenowe</h3>
      <div className="divide-y divide-border/50">
        {sorted.map((pattern, i) => (
          <button
            key={`${pattern.pattern_type}-${i}`}
            onClick={() => onPatternClick?.(pattern.pattern_type)}
            className="flex w-full items-start gap-4 px-4 py-3 text-left transition-colors hover:bg-border/20"
          >
            {/* Icon */}
            <span className="mt-0.5 text-xl">{pattern.bullish ? "📈" : "📉"}</span>

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{pattern.pattern_type}</span>
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                    pattern.bullish ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"
                  }`}
                >
                  {pattern.bullish ? "Bycza" : "Niedźwiedzia"}
                </span>
              </div>
              {pattern.description && <p className="mt-1 text-sm text-muted">{pattern.description}</p>}
              {pattern.location && <p className="mt-0.5 text-xs text-muted">Lokalizacja: {pattern.location}</p>}
            </div>

            {/* Confidence bar */}
            <div className="w-20 flex-shrink-0">
              <div className="mb-1 text-right text-xs text-muted">{Math.round(pattern.confidence * 100)}%</div>
              <div className="h-1.5 overflow-hidden rounded-full bg-border">
                <div
                  className={`h-full rounded-full ${confidenceBarClass(pattern.confidence * 100)}`}
                  style={{ width: `${pattern.confidence * 100}%` }}
                />
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
