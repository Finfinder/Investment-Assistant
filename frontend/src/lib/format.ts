/**
 * Return a Tailwind background-color class for a confidence bar.
 * @param pct confidence percentage 0-100
 */
export function confidenceBarClass(pct: number): string {
  if (pct >= 70) return "bg-green-400";
  if (pct >= 40) return "bg-yellow-400";
  return "bg-red-400";
}
