import type { SignalType } from "@/types";
import { SIGNAL_LABELS } from "@/lib/signals";

const SIGNAL_COLORS: Record<SignalType, string> = {
  strong_buy: "text-green-400 bg-green-400/10",
  buy: "text-green-300 bg-green-300/10",
  neutral: "text-gray-400 bg-gray-400/10",
  sell: "text-red-300 bg-red-300/10",
  strong_sell: "text-red-400 bg-red-400/10",
};

export function SignalBadge({ signal }: Readonly<{ signal: SignalType }>) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${SIGNAL_COLORS[signal]}`}>
      {SIGNAL_LABELS[signal]}
    </span>
  );
}

export function formatValue(value: number | null | undefined): string {
  if (value == null) return "—";
  return Number.isInteger(value) ? value.toString() : value.toFixed(4);
}
