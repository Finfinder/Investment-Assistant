import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ProgressIndicator from "@/components/ProgressIndicator";
import type { AnalysisStatus } from "@/types";

// Mock the WebSocket API
const mockWebSocket = {
  onmessage: null as ((event: MessageEvent) => void) | null,
  onerror: null as ((event: Event) => void) | null,
  onclose: null as ((event: CloseEvent) => void) | null,
  onopen: null as ((event: Event) => void) | null,
  close: vi.fn(),
};

const mockConnectAnalysisWebSocket = vi.fn();

vi.mock("@/lib/api", () => ({
  connectAnalysisWebSocket: (
    _analysisId: string,
    onMessage: (status: AnalysisStatus) => void,
    onError?: (error: Event) => void,
  ) => {
    mockConnectAnalysisWebSocket(onMessage, onError);
    return mockWebSocket as unknown as WebSocket;
  },
}));

describe("ProgressIndicator", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renderuje pasek postępu z odpowiednim procentem", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    render(<ProgressIndicator analysisId="test-id" onComplete={onComplete} onError={onError} />);

    // Initially shows 0%
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("wyświetla wszystkie 6 kroków pipeline'u", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    render(<ProgressIndicator analysisId="test-id" onComplete={onComplete} onError={onError} />);

    expect(screen.getByText("Pobieranie danych")).toBeInTheDocument();
    expect(screen.getByText("Analiza techniczna")).toBeInTheDocument();
    expect(screen.getByText("Rozpoznawanie formacji")).toBeInTheDocument();
    expect(screen.getByText("Analiza fundamentalna")).toBeInTheDocument();
    expect(screen.getByText("Agregacja sygnałów")).toBeInTheDocument();
    expect(screen.getByText("Generowanie strategii")).toBeInTheDocument();
  });

  it("stan 'failed' wyświetla komunikat błędu", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    // Mock the WebSocket to immediately send a failed status
    mockConnectAnalysisWebSocket.mockImplementation((onMessage: (status: AnalysisStatus) => void) => {
      onMessage({
        id: "test-id",
        status: "failed",
        progress_pct: 50,
        current_step: "Analiza techniczna",
        steps_completed: ["Pobieranie danych"],
        error_message: "Błąd połączenia z API",
      });
    });

    render(<ProgressIndicator analysisId="test-id" onComplete={onComplete} onError={onError} />);

    expect(screen.getByText("Błąd połączenia z API")).toBeInTheDocument();
  });

  it("wywołuje onComplete gdy status completed", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    mockConnectAnalysisWebSocket.mockImplementation((onMessage: (status: AnalysisStatus) => void) => {
      onMessage({
        id: "test-id",
        status: "completed",
        progress_pct: 100,
        current_step: "Generowanie strategii",
        steps_completed: [
          "Pobieranie danych",
          "Analiza techniczna",
          "Rozpoznawanie formacji",
          "Analiza fundamentalna",
          "Agregacja sygnałów",
          "Generowanie strategii",
        ],
        error_message: null,
      });
    });

    render(<ProgressIndicator analysisId="test-id" onComplete={onComplete} onError={onError} />);

    expect(onComplete).toHaveBeenCalled();
  });

  it("wywołuje onError gdy status failed", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    mockConnectAnalysisWebSocket.mockImplementation((onMessage: (status: AnalysisStatus) => void) => {
      onMessage({
        id: "test-id",
        status: "failed",
        progress_pct: 50,
        current_step: "Analiza techniczna",
        steps_completed: ["Pobieranie danych"],
        error_message: "Test error message",
      });
    });

    render(<ProgressIndicator analysisId="test-id" onComplete={onComplete} onError={onError} />);

    expect(onError).toHaveBeenCalledWith("Test error message");
  });
});