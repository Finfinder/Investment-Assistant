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
  return `1:${(1 / ratio).toFixed(2)}`;
}

/** Return a Tailwind text-color class for a risk/reward ratio. */
export function riskRewardClass(ratio: number | null): string {
  if (ratio === null) return "text-muted";
  if (ratio <= 0.5) return "text-green-400";
  return "text-yellow-400";
}
