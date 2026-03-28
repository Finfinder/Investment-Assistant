"use client";

import { useEffect, useRef, useCallback, useMemo } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
  LineStyle,
} from "lightweight-charts";
import type { OHLCVData, MovingAverage, PivotPoints, PatternDetection, InstrumentType, Timeframe } from "@/types";

interface CandlestickChartProps {
  ohlcvData: OHLCVData[];
  movingAverages: MovingAverage[];
  pivotPoints: PivotPoints[];
  patterns: PatternDetection[];
  highlightedPattern?: string | null;
  symbol: string;
  instrumentType: InstrumentType | null;
  timeframe: Timeframe;
}

function toChartTime(timestamp: string): UTCTimestamp {
  return Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp;
}

interface PriceLevelDef {
  value: number | null;
  color: string;
  label: string;
  style: typeof LineStyle.Dashed | typeof LineStyle.Dotted | typeof LineStyle.Solid;
  axisLabel: boolean;
}

function addPriceLines(series: ISeriesApi<"Candlestick">, levels: Readonly<PriceLevelDef[]>): void {
  for (const level of levels) {
    if (level.value != null) {
      series.createPriceLine({
        price: level.value,
        color: level.color,
        lineWidth: 1 as const,
        lineStyle: level.style,
        axisLabelVisible: level.axisLabel,
        title: level.label,
      });
    }
  }
}

function buildEmaLevels(movingAverages: Readonly<MovingAverage[]>): PriceLevelDef[] {
  const levels: PriceLevelDef[] = [];
  const ema50 = movingAverages.find((ma) => ma.period === 50);
  if (ema50?.ema_value != null) {
    levels.push({ value: ema50.ema_value, color: "#3b82f6", label: "EMA 50", style: LineStyle.Solid, axisLabel: true });
  }
  const ema200 = movingAverages.find((ma) => ma.period === 200);
  if (ema200?.ema_value != null) {
    levels.push({ value: ema200.ema_value, color: "#ef4444", label: "EMA 200", style: LineStyle.Solid, axisLabel: true });
  }
  return levels;
}

function buildClassicPivotLevels(pivotPoints: Readonly<PivotPoints[]>): PriceLevelDef[] {
  const classicPivot = pivotPoints.find((p) => p.type === "classic");
  if (!classicPivot) return [];
  return [
    { value: classicPivot.r3, color: "#ef4444", label: "R3", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.r2, color: "#f87171", label: "R2", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.r1, color: "#fca5a5", label: "R1", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.pp, color: "#eab308", label: "PP", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.s1, color: "#86efac", label: "S1", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.s2, color: "#4ade80", label: "S2", style: LineStyle.Dashed, axisLabel: true },
    { value: classicPivot.s3, color: "#22c55e", label: "S3", style: LineStyle.Dashed, axisLabel: true },
  ];
}

function buildFibonacciLevels(pivotPoints: Readonly<PivotPoints[]>): PriceLevelDef[] {
  const fibPivot = pivotPoints.find((p) => p.type === "fibonacci");
  if (!fibPivot) return [];
  return [
    { value: fibPivot.r3, color: "#a78bfa", label: "Fib R3", style: LineStyle.Dotted, axisLabel: false },
    { value: fibPivot.r2, color: "#a78bfa", label: "Fib R2", style: LineStyle.Dotted, axisLabel: false },
    { value: fibPivot.r1, color: "#a78bfa", label: "Fib R1", style: LineStyle.Dotted, axisLabel: false },
    { value: fibPivot.s1, color: "#a78bfa", label: "Fib S1", style: LineStyle.Dotted, axisLabel: false },
    { value: fibPivot.s2, color: "#a78bfa", label: "Fib S2", style: LineStyle.Dotted, axisLabel: false },
    { value: fibPivot.s3, color: "#a78bfa", label: "Fib S3", style: LineStyle.Dotted, axisLabel: false },
  ];
}

function buildPatternMarkers(
  patterns: Readonly<PatternDetection[]>,
  lastTimestamp: UTCTimestamp,
  highlightedPattern: string | null | undefined,
) {
  return patterns.map((p) => {
    const isHighlighted = highlightedPattern === p.pattern_type;
    const baseColor = p.bullish ? "#22c55e" : "#ef4444";
    return {
      time: lastTimestamp,
      position: p.bullish ? ("belowBar" as const) : ("aboveBar" as const),
      color: isHighlighted ? "#eab308" : baseColor,
      shape: p.bullish ? ("arrowUp" as const) : ("arrowDown" as const),
      text: p.pattern_type,
    };
  });
}

function getPriceFormat(instrumentType: InstrumentType | null, symbol: string) {
  if (instrumentType === "forex") {
    if (/JPY/i.test(symbol)) {
      return { type: "price" as const, precision: 2, minMove: 0.01 };
    }
    return { type: "price" as const, precision: 4, minMove: 0.0001 };
  }
  if (instrumentType === "commodity" && /^(XAGUSD|SILVER)$/i.test(symbol)) {
    return { type: "price" as const, precision: 3, minMove: 0.001 };
  }
  return { type: "price" as const, precision: 2, minMove: 0.01 };
}

const VISIBLE_BARS_BY_TIMEFRAME: Record<Timeframe, number | null> = {
  M15: 100,
  H1: 120,
  H4: 120,
  D1: null,
};

export default function CandlestickChart({
  ohlcvData,
  movingAverages,
  pivotPoints,
  patterns,
  highlightedPattern,
  symbol,
  instrumentType,
  timeframe,
}: Readonly<CandlestickChartProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const wheelCleanupRef = useRef<(() => void) | null>(null);

  const buildChart = useCallback(() => {
    if (!containerRef.current || ohlcvData.length === 0) return;

    if (chartRef.current) {
      wheelCleanupRef.current?.();
      wheelCleanupRef.current = null;
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#1a1d27" },
        textColor: "#e5e7eb",
      },
      grid: {
        vertLines: { color: "#2d3044" },
        horzLines: { color: "#2d3044" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#2d3044" },
      timeScale: { borderColor: "#2d3044", timeVisible: true },
      width: containerRef.current.clientWidth,
      height: 450,
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderDownColor: "#ef4444",
      borderUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      priceFormat: getPriceFormat(instrumentType, symbol),
    });
    candleSeriesRef.current = candleSeries;

    const candleData = ohlcvData.map((d) => ({
      time: toChartTime(d.timestamp),
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    candleSeries.setData(candleData as Parameters<typeof candleSeries.setData>[0]);

    // EMA levels as horizontal price lines (backend provides snapshot values, not time series)
    addPriceLines(candleSeries, buildEmaLevels(movingAverages));

    // S/R levels from Classic pivot points
    addPriceLines(candleSeries, buildClassicPivotLevels(pivotPoints));

    // Fibonacci levels
    addPriceLines(candleSeries, buildFibonacciLevels(pivotPoints));

    const dataLength = ohlcvData.length;
    const bars = VISIBLE_BARS_BY_TIMEFRAME[timeframe] ?? null;
    if (bars !== null && dataLength > bars) {
      chart.timeScale().setVisibleLogicalRange({ from: dataLength - bars, to: dataLength - 1 });
    } else {
      chart.timeScale().fitContent();
    }

    // Zoom anchoring — keep right edge pinned when zooming with mouse wheel
    let isAtRightEdge = true;
    let adjusting = false;

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (adjusting || !range) return;
      isAtRightEdge = range.to >= dataLength - 2;
    });

    const handleWheel = () => {
      if (!isAtRightEdge) return;
      adjusting = true;
      requestAnimationFrame(() => {
        const range = chart.timeScale().getVisibleLogicalRange();
        if (range) {
          const width = range.to - range.from;
          chart.timeScale().setVisibleLogicalRange({ from: dataLength - 1 - width, to: dataLength - 1 });
        }
        adjusting = false;
      });
    };

    containerRef.current.addEventListener("wheel", handleWheel, { passive: true });
    wheelCleanupRef.current = () => {
      containerRef.current?.removeEventListener("wheel", handleWheel);
    };
  }, [ohlcvData, movingAverages, pivotPoints, symbol, instrumentType, timeframe]);

  useEffect(() => {
    buildChart();
    return () => {
      wheelCleanupRef.current?.();
      wheelCleanupRef.current = null;
    };
  }, [buildChart]);

  // Update pattern markers without rebuilding the chart
  const lastTimestamp = useMemo(
    () => (ohlcvData.length > 0 ? toChartTime(ohlcvData.at(-1)!.timestamp) : (0 as UTCTimestamp)),
    [ohlcvData],
  );

  useEffect(() => {
    const series = candleSeriesRef.current;
    if (!series || ohlcvData.length === 0) return;

    if (patterns.length > 0) {
      const markers = buildPatternMarkers(patterns, lastTimestamp, highlightedPattern);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      createSeriesMarkers(series as any, markers as any);
    }
  }, [patterns, highlightedPattern, ohlcvData.length, lastTimestamp]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (chartRef.current) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const chartDescription = ohlcvData.length > 0
    ? `Wykres świecowy: ${ohlcvData.length} świec, zakres ${ohlcvData[0].timestamp.slice(0, 10)} – ${ohlcvData.at(-1)!.timestamp.slice(0, 10)}`
    : "Wykres świecowy – brak danych";

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="mb-3 text-lg font-semibold">Wykres</h3>
      <figure aria-label={chartDescription}>
        <div ref={containerRef} className="w-full" />
      </figure>
    </div>
  );
}
