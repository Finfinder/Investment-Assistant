import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// Scenario 1: Market data (cached) — response ≤ 3s
export const options = {
  scenarios: {
    market_data_cached: {
      executor: "constant-vus",
      vus: 1,
      duration: "10s",
      exec: "marketDataCached",
      tags: { scenario: "market_data_cached" },
    },
    full_analysis: {
      executor: "per-vu-iterations",
      vus: 1,
      iterations: 1,
      exec: "fullAnalysis",
      tags: { scenario: "full_analysis" },
      startTime: "0s",
    },
    parallel_analyses: {
      executor: "per-vu-iterations",
      vus: 3,
      iterations: 1,
      exec: "fullAnalysis",
      tags: { scenario: "parallel_analyses" },
      startTime: "15s",
    },
  },
  thresholds: {
    "http_req_duration{scenario:market_data_cached}": ["p(95)<3000"],
    "http_req_duration{scenario:full_analysis}": ["max<300000"],
    "http_req_duration{scenario:parallel_analyses}": ["max<300000"],
  },
};

// Scenario 1: Cached market data — must respond within 3s
export function marketDataCached() {
  const res = http.get(`${BASE_URL}/api/v1/market-data/EURUSD?timeframe=H1&period=30d`);
  check(res, {
    "market-data status 200": (r) => r.status === 200,
    "market-data response < 3s": (r) => r.timings.duration < 3000,
  });
  sleep(1);
}

// Scenario 2 & 3: Full analysis pipeline — must complete within 5 minutes
export function fullAnalysis() {
  const triggerRes = http.post(
    `${BASE_URL}/api/v1/analysis`,
    JSON.stringify({ symbol: "EURUSD", timeframe: "H1" }),
    { headers: { "Content-Type": "application/json" } },
  );

  check(triggerRes, {
    "trigger status 200": (r) => r.status === 200,
  });

  if (triggerRes.status !== 200) return;

  const analysisId = triggerRes.json("analysis_id");
  const deadline = Date.now() + 300_000; // 5 minutes

  while (Date.now() < deadline) {
    const statusRes = http.get(`${BASE_URL}/api/v1/analysis/${analysisId}/status`);
    if (statusRes.status !== 200) break;

    const status = statusRes.json("status");
    if (status === "completed" || status === "failed") {
      check(statusRes, {
        "analysis completed": () => status === "completed",
      });
      break;
    }
    sleep(2);
  }

  const reportRes = http.get(`${BASE_URL}/api/v1/analysis/${analysisId}`);
  check(reportRes, {
    "report status 200": (r) => r.status === 200,
  });
}
