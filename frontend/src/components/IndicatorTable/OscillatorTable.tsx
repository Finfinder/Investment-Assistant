import type { IndicatorValue } from "@/types";
import { SignalBadge, formatValue } from "./shared";

interface OscillatorTableProps {
  indicators: IndicatorValue[];
}

export default function OscillatorTable({ indicators }: Readonly<OscillatorTableProps>) {
  if (indicators.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-card">
      <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Oscylatory</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Oscylatory – wartości i sygnały</caption>
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="px-4 py-2 font-medium">Nazwa</th>
              <th className="px-4 py-2 font-medium">Wartość</th>
              <th className="px-4 py-2 font-medium">Sygnał</th>
            </tr>
          </thead>
          <tbody>
            {indicators.map((ind) => (
              <tr key={ind.name} className="border-b border-border/50 hover:bg-border/20">
                <td className="px-4 py-2 font-medium">{ind.name}</td>
                <td className="px-4 py-2 font-mono text-sm">{formatValue(ind.value)}</td>
                <td className="px-4 py-2">
                  <SignalBadge signal={ind.signal} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
