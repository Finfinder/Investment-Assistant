import type { SignalType } from "@/types";
import { SIGNAL_LABELS } from "@/lib/signals";

interface SignalGaugeProps {
  label: string;
  signal: SignalType;
  buyCount: number;
  sellCount: number;
  neutralCount: number;
}

const SIGNAL_POSITION: Record<SignalType, number> = {
  strong_sell: 0,
  sell: 25,
  neutral: 50,
  buy: 75,
  strong_buy: 100,
};

const SIGNAL_COLOR: Record<SignalType, string> = {
  strong_sell: "#ef4444",
  sell: "#f87171",
  neutral: "#eab308",
  buy: "#4ade80",
  strong_buy: "#22c55e",
};

export default function SignalGauge({ label, signal, buyCount, sellCount, neutralCount }: Readonly<SignalGaugeProps>) {
  const position = SIGNAL_POSITION[signal];
  const color = SIGNAL_COLOR[signal];
  const total = buyCount + sellCount + neutralCount;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h4 className="mb-3 text-center text-sm font-medium text-muted">{label}</h4>

      {/* Gauge bar */}
      <div className="relative mb-2 h-3 overflow-hidden rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500">
        <div
          className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-lg transition-all duration-500"
          style={{ left: `${position}%`, backgroundColor: color }}
        />
      </div>
      <span className="sr-only">{label}: {SIGNAL_LABELS[signal]}</span>

      {/* Labels */}
      <div className="mb-3 flex justify-between text-xs text-muted">
        <span>Mocne Sprzedaj</span>
        <span>Neutralny</span>
        <span>Mocne Kup</span>
      </div>

      {/* Signal label */}
      <div className="mb-3 text-center text-lg font-bold" style={{ color }}>
        {SIGNAL_LABELS[signal]}
      </div>

      {/* Counts */}
      {total > 0 && (
        <div className="flex justify-center gap-4 text-xs">
          <span className="text-green-400">Kup: {buyCount}</span>
          <span className="text-gray-400">Neutralny: {neutralCount}</span>
          <span className="text-red-400">Sprzedaj: {sellCount}</span>
        </div>
      )}
    </div>
  );
}
