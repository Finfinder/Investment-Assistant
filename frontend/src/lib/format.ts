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

/**
 * Próg, powyżej którego R/R jest klasyfikowany jako "umiarkowany" (żółty).
 * Wartości z przedziału [0, RISK_REWARD_FAVORABLE_THRESHOLD] oznaczają setup korzystny (zielony).
 * Próg ma znaczenie domenowe (granica "korzystne/umiarkowane") ustalone w Issue #126.
 */
const RISK_REWARD_FAVORABLE_THRESHOLD = 0.5;

/**
 * Return a Tailwind text-color class for a risk/reward ratio.
 * Semantyka kolorów: zielony = korzystne (0 <= R/R <= próg), czerwony = niekorzystne (R/R < 0),
 * żółty = umiarkowane (R/R > próg), muted = brak danych (null).
 */
export function riskRewardClass(ratio: number | null): string {
  if (ratio === null) return "text-muted";
  if (ratio < 0) return "text-red-400";
  if (ratio <= RISK_REWARD_FAVORABLE_THRESHOLD) return "text-green-400";
  return "text-yellow-400";
}
