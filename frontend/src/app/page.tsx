"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import type { Timeframe, AnalysisReport } from "@/types";
import { triggerAnalysis, getAnalysis } from "@/lib/api";
import AnalysisForm from "@/components/AnalysisForm";
import ProgressIndicator from "@/components/ProgressIndicator";
import OscillatorTable from "@/components/IndicatorTable/OscillatorTable";
import MovingAverageTable from "@/components/IndicatorTable/MovingAverageTable";
import PivotTable from "@/components/PivotPoints/PivotTable";
import SignalGauge from "@/components/SignalSummary/SignalGauge";
import PatternList from "@/components/Patterns/PatternList";
import FundamentalPanel from "@/components/Fundamental/FundamentalPanel";
import StrategyTable from "@/components/Strategy/StrategyTable";
import Section from "@/components/Section";

const CandlestickChart = dynamic(() => import("@/components/Chart/CandlestickChart"), { ssr: false });

type AppState = "idle" | "analyzing" | "done" | "error";

const SECTION_NAV = [
  { id: "signals", label: "Sygnały" },
  { id: "chart", label: "Wykres" },
  { id: "strategies", label: "Strategie" },
  { id: "indicators", label: "Wskaźniki" },
  { id: "pivots", label: "Pivot Points" },
  { id: "patterns", label: "Formacje" },
  { id: "fundamental", label: "Fundamenty" },
] as const;

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function HomePage() {
  const [state, setState] = useState<AppState>("idle");
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string>("");
  const [highlightedPattern, setHighlightedPattern] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Scroll spy: observe sections to highlight active nav item
  useEffect(() => {
    if (state !== "done") return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: "-20% 0px -60% 0px" },
    );

    const observer = observerRef.current;
    for (const { id } of SECTION_NAV) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [state]);

  const handleSubmit = useCallback(async (symbol: string, timeframe: Timeframe) => {
    setState("analyzing");
    setError("");
    setReport(null);
    try {
      const response = await triggerAnalysis({ symbol, timeframe });
      setAnalysisId(response.analysis_id);
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Nie udało się uruchomić analizy");
    }
  }, []);

  const handleAnalysisComplete = useCallback(async () => {
    if (!analysisId) return;
    try {
      const result = await getAnalysis(analysisId);
      if ("symbol" in result) {
        setReport(result);
        setState("done");
      } else {
        setState("error");
        setError("Nie udało się pobrać raportu");
      }
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Błąd pobierania raportu");
    }
  }, [analysisId]);

  const handleAnalysisError = useCallback((message: string) => {
    setState("error");
    setError(message);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky header */}
      {report && (
        <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold">{report.symbol}</h1>
              <span className="rounded bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                {report.timeframe}
              </span>
            </div>
            <time className="text-sm text-muted">{new Date(report.timestamp).toLocaleString("pl-PL")}</time>
          </div>
          <nav className="mx-auto max-w-7xl overflow-x-auto px-4 pb-2" aria-label="Sekcje raportu">
            <ul className="flex gap-1 text-xs">
              {SECTION_NAV.map(({ id, label }) => (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => scrollToSection(id)}
                    className={`whitespace-nowrap rounded-full px-3 py-1 transition-colors ${
                      activeSection === id ? "bg-accent text-white" : "text-muted hover:bg-border"
                    }`}
                  >
                    {label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </header>
      )}

      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Title */}
        {!report && (
          <div className="mb-8 text-center">
            <h1 className="mb-2 text-3xl font-bold">Investment Assistant</h1>
            <p className="text-muted">Analiza techniczna, fundamentalna i rozpoznawanie formacji dla instrumentów CFD</p>
          </div>
        )}

        {/* Form */}
        <div className="mb-8">
          <AnalysisForm onSubmit={handleSubmit} isLoading={state === "analyzing"} />
        </div>

        {/* Error */}
        {state === "error" && (
          <div role="alert" className="mb-8 rounded-xl border border-danger/30 bg-danger/10 p-4 text-center text-danger">{error}</div>
        )}

        {/* Progress */}
        {state === "analyzing" && analysisId && (
          <div className="mb-8" aria-live="polite">
            <ProgressIndicator
              analysisId={analysisId}
              onComplete={handleAnalysisComplete}
              onError={handleAnalysisError}
            />
          </div>
        )}

        {/* Report */}
        {state === "done" && report && (
          <div className="space-y-6">
            {/* Signal Summary Gauges */}
            {report.signal_summary && (
              <Section title="Podsumowanie sygnałów" id="signals">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <SignalGauge
                    label="Średnie kroczące"
                    signal={report.signal_summary.ma_summary}
                    buyCount={report.signal_summary.ma_buy_count}
                    sellCount={report.signal_summary.ma_sell_count}
                    neutralCount={report.signal_summary.ma_neutral_count}
                  />
                  <SignalGauge
                    label="Wskaźniki"
                    signal={report.signal_summary.indicators_summary}
                    buyCount={report.signal_summary.indicators_buy_count}
                    sellCount={report.signal_summary.indicators_sell_count}
                    neutralCount={report.signal_summary.indicators_neutral_count}
                  />
                  <SignalGauge
                    label="Ogólnie"
                    signal={report.signal_summary.overall_summary}
                    buyCount={report.signal_summary.overall_buy_count}
                    sellCount={report.signal_summary.overall_sell_count}
                    neutralCount={report.signal_summary.overall_neutral_count}
                  />
                </div>
              </Section>
            )}

            {/* Chart */}
            {report.ohlcv_data.length > 0 && (
              <Section title="Wykres" id="chart">
                <CandlestickChart
                  ohlcvData={report.ohlcv_data}
                  movingAverages={report.moving_averages}
                  pivotPoints={report.pivot_points}
                  patterns={report.patterns}
                  highlightedPattern={highlightedPattern}
                />
              </Section>
            )}

            {/* Strategy */}
            <Section title="Strategie wejścia" id="strategies">
              <StrategyTable strategies={report.strategies} />
            </Section>

            {/* Indicators */}
            <Section title="Wskaźniki techniczne" id="indicators">
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <OscillatorTable indicators={report.technical_indicators} />
                <MovingAverageTable movingAverages={report.moving_averages} />
              </div>
            </Section>

            {/* Pivot Points */}
            <Section title="Pivot Points" id="pivots">
              <PivotTable pivotPoints={report.pivot_points} />
            </Section>

            {/* Patterns */}
            <Section title="Formacje cenowe" id="patterns">
              <PatternList patterns={report.patterns} onPatternClick={setHighlightedPattern} />
            </Section>

            {/* Fundamental */}
            {report.fundamental && (
              <Section title="Analiza fundamentalna" id="fundamental">
                <FundamentalPanel fundamental={report.fundamental} />
              </Section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
