"use client";

import type { ChartLayerVisibility } from "@/types";

interface ChartToolbarProps {
  visibility: ChartLayerVisibility;
  onChange: (v: ChartLayerVisibility) => void;
}

interface LayerConfig {
  key: keyof ChartLayerVisibility;
  label: string;
  activeClass: string;
  inactiveClass: string;
}

const LAYERS: LayerConfig[] = [
  {
    key: "ema",
    label: "EMA",
    activeClass: "bg-blue-600 border-blue-600 text-white",
    inactiveClass: "border-blue-600 text-blue-400 hover:bg-blue-600/10",
  },
  {
    key: "pivotPoints",
    label: "Pivot Points",
    activeClass: "bg-yellow-700 border-yellow-700 text-white",
    inactiveClass: "border-yellow-600 text-yellow-400 hover:bg-yellow-600/10",
  },
  {
    key: "fibonacci",
    label: "Fibonacci",
    activeClass: "bg-purple-700 border-purple-700 text-white",
    inactiveClass: "border-purple-600 text-purple-400 hover:bg-purple-600/10",
  },
  {
    key: "patterns",
    label: "Formacje",
    activeClass: "bg-green-700 border-green-700 text-white",
    inactiveClass: "border-green-600 text-green-400 hover:bg-green-600/10",
  },
];

export default function ChartToolbar({ visibility, onChange }: Readonly<ChartToolbarProps>) {
  function toggle(key: keyof ChartLayerVisibility) {
    onChange({ ...visibility, [key]: !visibility[key] });
  }

  return (
    <div className="mb-2 flex flex-wrap gap-2">
      {LAYERS.map(({ key, label, activeClass, inactiveClass }) => (
        <button
          key={key}
          type="button"
          aria-pressed={visibility[key]}
          onClick={() => toggle(key)}
          className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
            visibility[key] ? activeClass : inactiveClass
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
