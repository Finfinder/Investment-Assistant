import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { vi } from "vitest";

// Only run browser mocks in jsdom environment
if (typeof window !== "undefined") {
  // Mock IntersectionObserver (used in page.tsx scroll spy)
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }

  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });

  // Mock ResizeObserver (used in CandlestickChart)
  class MockResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }

  Object.defineProperty(window, "ResizeObserver", {
    writable: true,
    configurable: true,
    value: MockResizeObserver,
  });

  // Mock WebSocket (used in ProgressIndicator)
  class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;
    onopen: ((event: Event) => void) | null = null;

    constructor(_url: string) {
      // Mock WebSocket constructor
    }

    close = vi.fn();
    send = vi.fn();
  }

  Object.defineProperty(window, "WebSocket", {
    writable: true,
    configurable: true,
    value: MockWebSocket,
  });

  // Mock localStorage
  const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        store = {};
      },
    };
  })();

  Object.defineProperty(window, "localStorage", {
    writable: true,
    configurable: true,
    value: localStorageMock,
  });
}
