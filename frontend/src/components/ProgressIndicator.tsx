"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { AnalysisStatus } from "@/types";
import { connectAnalysisWebSocket } from "@/lib/api";

const MAX_RECONNECT_ATTEMPTS = 5;

const PIPELINE_STEPS = [
  "Pobieranie danych",
  "Analiza techniczna",
  "Rozpoznawanie formacji",
  "Analiza fundamentalna",
  "Agregacja sygnałów",
  "Generowanie strategii",
];

interface ProgressIndicatorProps {
  analysisId: string;
  onComplete: () => void | Promise<void>;
  onError: (message: string) => void | Promise<void>;
}

function StepIcon({ isCompleted, isCurrent }: Readonly<{ isCompleted: boolean; isCurrent: boolean }>) {
  if (isCompleted) {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-success text-xs text-white">
        ✓
      </span>
    );
  }
  if (isCurrent) {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-accent">
        <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-border">
      <span className="h-2 w-2 rounded-full bg-border" />
    </span>
  );
}

function stepTextClass(isCompleted: boolean, isCurrent: boolean): string {
  if (isCompleted) return "text-success";
  if (isCurrent) return "text-accent";
  return "text-muted";
}

export default function ProgressIndicator({ analysisId, onComplete, onError }: Readonly<ProgressIndicatorProps>) {
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const connect = useCallback(() => {
    const ws = connectAnalysisWebSocket(
      analysisId,
      (s) => {
        reconnectAttempt.current = 0;
        setStatus(s);
        if (s.status === "completed") {
          void onCompleteRef.current();
        } else if (s.status === "failed") {
          void onErrorRef.current(s.error_message || "Analiza zakończyła się błędem");
        }
      },
      () => {
        if (reconnectAttempt.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(1000 * 2 ** reconnectAttempt.current, 16000);
          reconnectAttempt.current += 1;
          reconnectTimer.current = setTimeout(connect, delay);
        } else {
          void onErrorRef.current("Utracono połączenie z serwerem");
        }
      },
    );
    wsRef.current = ws;
  }, [analysisId]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const completedSteps = status?.steps_completed ?? [];
  const currentStep = status?.current_step ?? "";
  const progressPct = status?.progress_pct ?? 0;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Postęp analizy</h3>
        <span className="text-sm text-muted">{Math.round(progressPct)}%</span>
      </div>

      {/* Progress bar */}
      <div className="mb-6 h-2 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {PIPELINE_STEPS.map((step) => {
          const isCompleted = completedSteps.some((c) => c.toLowerCase().includes(step.toLowerCase().split(" ")[0]));
          const isCurrent = currentStep.toLowerCase().includes(step.toLowerCase().split(" ")[0]);

          return (
            <div key={step} className="flex items-center gap-3">
              <StepIcon isCompleted={isCompleted} isCurrent={isCurrent} />
              <span className={stepTextClass(isCompleted, isCurrent)}>{step}</span>
            </div>
          );
        })}
      </div>

      {status?.status === "failed" && (
        <div className="mt-4 rounded-lg bg-danger/10 p-3 text-sm text-danger">
          {status.error_message || "Wystąpił błąd podczas analizy"}
        </div>
      )}
    </div>
  );
}
