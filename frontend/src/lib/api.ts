import type { AnalysisReport, AnalysisRequest, AnalysisResponse, AnalysisStatus } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export async function triggerAnalysis(request: AnalysisRequest): Promise<AnalysisResponse> {
  return apiFetch<AnalysisResponse>("/analysis", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getAnalysis(analysisId: string): Promise<AnalysisReport | AnalysisStatus> {
  return apiFetch<AnalysisReport | AnalysisStatus>(`/analysis/${encodeURIComponent(analysisId)}`);
}

export async function getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
  return apiFetch<AnalysisStatus>(`/analysis/${encodeURIComponent(analysisId)}/status`);
}

export function connectAnalysisWebSocket(
  analysisId: string,
  onMessage: (status: AnalysisStatus) => void,
  onError?: (error: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/analysis/${encodeURIComponent(analysisId)}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as AnalysisStatus;
      onMessage(data);
    } catch {
      // Ignore malformed messages
    }
  };

  ws.onerror = (event) => {
    onError?.(event);
  };

  return ws;
}
