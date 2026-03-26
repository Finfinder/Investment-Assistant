import type { MovingAverage } from "@/types";
import { SignalBadge, formatValue } from "./shared";

interface MovingAverageTableProps {
  movingAverages: MovingAverage[];
}

export default function MovingAverageTable({ movingAverages }: Readonly<MovingAverageTableProps>) {
  if (movingAverages.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-card">
      <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Średnie kroczące</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Średnie kroczace – SMA i EMA</caption>
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="px-4 py-2 font-medium">Okres</th>
              <th className="px-4 py-2 font-medium">SMA</th>
              <th className="px-4 py-2 font-medium">Sygnał SMA</th>
              <th className="px-4 py-2 font-medium">EMA</th>
              <th className="px-4 py-2 font-medium">Sygnał EMA</th>
            </tr>
          </thead>
          <tbody>
            {movingAverages.map((ma) => (
              <tr key={ma.period} className="border-b border-border/50 hover:bg-border/20">
                <td className="px-4 py-2 font-medium">MA({ma.period})</td>
                <td className="px-4 py-2 font-mono text-sm">{formatValue(ma.sma_value)}</td>
                <td className="px-4 py-2">
                  <SignalBadge signal={ma.sma_signal} />
                </td>
                <td className="px-4 py-2 font-mono text-sm">{formatValue(ma.ema_value)}</td>
                <td className="px-4 py-2">
                  <SignalBadge signal={ma.ema_signal} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
