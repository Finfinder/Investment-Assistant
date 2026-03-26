import type { StrategyEntry } from "@/types";
import { formatValue } from "../IndicatorTable/shared";
import { confidenceBarClass } from "@/lib/format";

interface StrategyTableProps {
  strategies: StrategyEntry[];
}

export default function StrategyTable({ strategies }: Readonly<StrategyTableProps>) {
  if (strategies.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center text-muted">
        Brak wygenerowanych strategii
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card">
      <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Strategie wejścia</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Strategie wejścia – parametry pozycji</caption>
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="px-4 py-2 font-medium">Kierunek</th>
              <th className="px-4 py-2 font-medium">Wejście</th>
              <th className="px-4 py-2 font-medium">Stop Loss</th>
              <th className="px-4 py-2 font-medium">TP1</th>
              <th className="px-4 py-2 font-medium">TP2</th>
              <th className="px-4 py-2 font-medium">Pewność</th>
            </tr>
          </thead>
          <tbody>
            {strategies.map((s, i) => (
              <tr key={`${s.direction}-${s.entry_price}-${i}`} className="border-b border-border/50 hover:bg-border/20">
                <td className="px-4 py-2">
                  <span
                    className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-bold ${
                      s.direction === "long" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"
                    }`}
                  >
                    {s.direction === "long" ? "▲ LONG" : "▼ SHORT"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="font-mono text-sm">{formatValue(s.entry_price)}</div>
                  {s.entry_condition && <div className="mt-0.5 text-xs text-muted">{s.entry_condition}</div>}
                </td>
                <td className="px-4 py-2 font-mono text-sm text-red-400">{formatValue(s.stop_loss)}</td>
                <td className="px-4 py-2 font-mono text-sm text-green-300">{formatValue(s.tp1)}</td>
                <td className="px-4 py-2 font-mono text-sm text-green-400">{formatValue(s.tp2)}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-border">
                      <div
                        className={`h-full rounded-full ${confidenceBarClass(s.confidence_pct)}`}
                        style={{ width: `${s.confidence_pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted">{s.confidence_pct.toFixed(0)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
