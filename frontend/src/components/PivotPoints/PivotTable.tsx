import type { PivotPoints } from "@/types";
import { formatValue } from "../IndicatorTable/shared";

interface PivotTableProps {
  pivotPoints: PivotPoints[];
}

const ROW_LABELS = ["S3", "S2", "S1", "PP", "R1", "R2", "R3"] as const;
const ROW_KEYS: Record<(typeof ROW_LABELS)[number], keyof PivotPoints> = {
  S3: "s3",
  S2: "s2",
  S1: "s1",
  PP: "pp",
  R1: "r1",
  R2: "r2",
  R3: "r3",
};

const ROW_COLORS: Record<string, string> = {
  S3: "text-green-400",
  S2: "text-green-300",
  S1: "text-green-200",
  PP: "text-yellow-300",
  R1: "text-red-200",
  R2: "text-red-300",
  R3: "text-red-400",
};

const TYPE_LABELS: Record<string, string> = {
  classic: "Classic",
  fibonacci: "Fibonacci",
  camarilla: "Camarilla",
  woodie: "Woodie",
  demark: "DeMark",
};

export default function PivotTable({ pivotPoints }: Readonly<PivotTableProps>) {
  if (pivotPoints.length === 0) return null;

  const isDemark = (type: string) => type === "demark";

  return (
    <div className="rounded-xl border border-border bg-card">
      <h3 className="border-b border-border px-4 py-3 text-lg font-semibold">Pivot Points</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Pivot Points – poziomy wsparcia i oporu</caption>
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="px-4 py-2 font-medium">Poziom</th>
              {pivotPoints.map((p) => (
                <th key={p.type} className="px-4 py-2 font-medium">
                  {TYPE_LABELS[p.type] || p.type}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROW_LABELS.map((label) => {
              // DeMark only has S1, PP, R1
              const key = ROW_KEYS[label];
              const hasAnyValue = pivotPoints.some((p) => {
                if (isDemark(p.type) && !["s1", "pp", "r1"].includes(key)) return false;
                return (p[key] as number | null) != null;
              });

              if (!hasAnyValue) return null;

              return (
                <tr key={label} className="border-b border-border/50 hover:bg-border/20">
                  <td className={`px-4 py-2 font-medium ${ROW_COLORS[label] || ""}`}>{label}</td>
                  {pivotPoints.map((p) => {
                    if (isDemark(p.type) && !["s1", "pp", "r1"].includes(key)) {
                      return (
                        <td key={p.type} className="px-4 py-2 text-muted">
                          —
                        </td>
                      );
                    }
                    return (
                      <td key={p.type} className="px-4 py-2 font-mono text-sm">
                        {formatValue(p[key] as number | null)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
