import type { FundamentalData } from "@/types";

interface FundamentalPanelProps {
  fundamental: FundamentalData;
}

const TYPE_LABELS: Record<string, string> = {
  forex: "Forex",
  commodity: "Surowce",
  index: "Indeksy",
};

function getScoreColor(score: number): string {
  if (score > 30) return "#22c55e";
  if (score > 0) return "#4ade80";
  if (score > -30) return "#eab308";
  return "#ef4444";
}

function getScoreLabel(score: number): string {
  if (score > 50) return "Mocne Kup";
  if (score > 15) return "Kup";
  if (score > -15) return "Neutralny";
  if (score > -50) return "Sprzedaj";
  return "Mocne Sprzedaj";
}

function ScoreBar({ score }: Readonly<{ score: number }>) {
  // Score ranges from -100 to +100
  const position = ((score + 100) / 200) * 100;
  const color = getScoreColor(score);
  const label = getScoreLabel(score);

  return (
    <div className="mb-4">
      <div className="mb-1 flex justify-between text-xs text-muted">
        <span>Niedźwiedzi (-100)</span>
        <span>Byczy (+100)</span>
      </div>
      <div className="relative h-3 overflow-hidden rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500">
        <div
          className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-lg transition-all duration-500"
          style={{ left: `${position}%`, backgroundColor: color }}
        />
      </div>
      <div className="mt-2 text-center text-lg font-bold" style={{ color }}>
        {label} ({score > 0 ? "+" : ""}{score.toFixed(0)})
      </div>
    </div>
  );
}

function formatIndicatorValue(value: number | string | null): string {
  if (value == null) return "—";
  if (typeof value === "string") return value;
  return Number.isInteger(value) ? value.toString() : value.toFixed(4);
}

export default function FundamentalPanel({ fundamental }: Readonly<FundamentalPanelProps>) {
  const indicators = Object.entries(fundamental.indicators);

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-lg font-semibold">Analiza fundamentalna</h3>
        <span className="rounded bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
          {TYPE_LABELS[fundamental.instrument_type] || fundamental.instrument_type}
        </span>
      </div>

      <div className="p-4">
        <ScoreBar score={fundamental.score} />

        {fundamental.summary && <p className="mb-4 text-sm text-muted">{fundamental.summary}</p>}

        {indicators.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted">
                  <th className="px-3 py-2 font-medium">Wskaźnik</th>
                  <th className="px-3 py-2 font-medium">Wartość</th>
                </tr>
              </thead>
              <tbody>
                {indicators.map(([key, value]) => (
                  <tr key={key} className="border-b border-border/50 hover:bg-border/20">
                    <td className="px-3 py-2 font-medium">{key}</td>
                    <td className="px-3 py-2 font-mono text-sm">{formatIndicatorValue(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
