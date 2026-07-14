/**
 * Return a Tailwind background-color class for a confidence bar.
 * @param pct confidence percentage 0-100
 */
export function confidenceBarClass(pct: number): string {
  if (pct >= 70) return "bg-green-400";
  if (pct >= 40) return "bg-yellow-400";
  return "bg-red-400";
}

/** Format risk/reward ratio as trading-standard "1:X.XX". */
export function formatRiskReward(ratio: number | null): string {
  if (ratio === null || ratio === 0) return "—";
  // NaN i Infinity to błędne dane — sygnalizujemy "∞" zamiast mylącego "1:0.00".
  if (!Number.isFinite(ratio)) return "∞";
  return `1:${(1 / ratio).toFixed(2)}`;
}

export { riskRewardClass } from "./riskReward";
