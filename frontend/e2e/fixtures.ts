import { test as base, type Page } from "@playwright/test";

const MOCK_ANALYSIS_ID = "mock-analysis-id";

function mockReport(symbol: string, timeframe: string) {
  const instrumentTypeMap: Record<string, string | null> = {
    EURUSD: "forex",
    GBPUSD: "forex",
    USDJPY: "forex",
    XAUUSD: "commodity",
    GOLD: "commodity",
    US500: "index",
    SPX: "index",
  };
  return {
    symbol,
    timeframe,
    timestamp: new Date().toISOString(),
    instrument_type: instrumentTypeMap[symbol] ?? null,
    timeframe_context: {
      pivot_points_timeframe: "D1",
      pattern_scanner_timeframes: ["D1", "H1", "M15"],
      long_term_trend_label: "weekly",
    },
    ohlcv_data: Array.from({ length: 30 }, (_, i) => ({
      timestamp: new Date(Date.now() - (30 - i) * 3600000).toISOString(),
      open: 1.1 + i * 0.001,
      high: 1.1 + i * 0.001 + 0.002,
      low: 1.1 + i * 0.001 - 0.001,
      close: 1.1 + i * 0.001 + 0.001,
      volume: 1000 + i * 100,
    })),
    technical_indicators: [
      { name: "RSI(14)", value: 55.3, signal: "neutral" },
      { name: "STOCH.K(9)", value: 65, signal: "buy" },
      { name: "CCI(14)", value: 45.2, signal: "neutral" },
      { name: "ADX(14)", value: 28.5, signal: "neutral" },
      { name: "AO", value: 0.0035, signal: "buy" },
      { name: "Momentum(10)", value: 0.012, signal: "buy" },
      { name: "MACD(12,26,9)", value: 0.0012, signal: "buy" },
      { name: "Williams %R(14)", value: -35.2, signal: "neutral" },
      { name: "UO(7,14,28)", value: 52.1, signal: "neutral" },
      { name: "ATR(14)", value: 0.0045, signal: "neutral" },
      { name: "BBP(13)", value: 0.0023, signal: "buy" },
      { name: "STOCHRSI.K(14)", value: 72.5, signal: "neutral" },
      { name: "ROC(15)", value: 1.25, signal: "buy" },
    ],
    moving_averages: [
      { period: 10, sma_value: 1.105, sma_signal: "buy", ema_value: 1.106, ema_signal: "buy" },
      { period: 20, sma_value: 1.1, sma_signal: "neutral", ema_value: 1.101, ema_signal: "neutral" },
      { period: 50, sma_value: 1.095, sma_signal: "sell", ema_value: 1.096, ema_signal: "sell" },
    ],
    pivot_points: [
      { type: "classic", pp: 1.105, s1: 1.1, s2: 1.095, s3: 1.09, r1: 1.11, r2: 1.115, r3: 1.12 },
    ],
    patterns: [
      {
        pattern_type: "Hammer",
        confidence: 0.85,
        description: "Formacja młota",
        location: "emerging",
        bullish: true,
        category: "candlestick",
        timeframe,
        detected_at_index: 29,
        detected_at_timestamp: new Date().toISOString(),
        relevance_score: 0.9,
        target_price: null,
        indication: "Odwrót bycza",
        reliability: 2,
        detailed_description: "Formacja młota pojawia się po trendzie spadkowym i sygnalizuje potencjalne odwrócenie na wzrostowy.",
      },
    ],
    pattern_scanner_results: [
      {
        pattern_type: "Hammer",
        category: "candlestick",
        bullish: true,
        confidence: 0.85,
        timeframes: ["D1", timeframe],
        representative_pattern: {
          pattern_type: "Hammer",
          confidence: 0.85,
          description: "Formacja młota",
          location: "emerging",
          bullish: true,
          category: "candlestick",
          timeframe,
          detected_at_index: 29,
          detected_at_timestamp: new Date().toISOString(),
          relevance_score: 0.9,
          target_price: null,
          indication: "Odwrót bycza",
          reliability: 2,
          detailed_description: "Formacja młota pojawia się po trendzie spadkowym i sygnalizuje potencjalne odwrócenie na wzrostowy.",
        },
      },
      {
        pattern_type: "Ascending Triangle",
        category: "chart_pattern",
        bullish: true,
        confidence: 0.72,
        timeframes: ["M15"],
        representative_pattern: {
          pattern_type: "Ascending Triangle",
          confidence: 0.72,
          description: "Formacja kontynuacji z rosnącymi minimami.",
          location: "completed",
          bullish: true,
          category: "chart_pattern",
          timeframe: "M15",
          detected_at_index: 18,
          detected_at_timestamp: new Date().toISOString(),
          relevance_score: 0.68,
          target_price: 1.128,
          indication: "Kontynuacja wzrostu",
          reliability: 2,
          detailed_description: "Trójkąt zwyżkujący sygnalizuje możliwość wybicia zgodnego z kierunkiem wcześniejszego trendu.",
        },
      },
      {
        pattern_type: "Doji",
        category: "candlestick",
        bullish: false,
        confidence: 0.55,
        timeframes: ["H1"],
        representative_pattern: {
          pattern_type: "Doji",
          confidence: 0.55,
          description: "Świeca Doji sygnalizująca niepewność rynku.",
          location: "current",
          bullish: false,
          category: "candlestick",
          timeframe: "H1",
          detected_at_index: 25,
          detected_at_timestamp: new Date().toISOString(),
          relevance_score: 0.45,
          target_price: null,
          indication: "Niedźwiedź",
          reliability: 1,
          detailed_description: "Doji pojawia się, gdy otwarte i zamknięcie ceny są bliskie sobie, co sugeruje równowagę między kupującymi a sprzedającymi.",
        },
      },
    ],
    long_term_trend: {
      signal: "buy",
      summary: "Trend wzrostowy",
      source_label: "weekly",
    },
    fundamental: {
      instrument_type: "forex",
      indicators: { interest_rate_diff: 1.5 },
      score: 6.5,
      summary: "Umiarkowanie pozytywne dane fundamentalne",
    },
    signal_summary: {
      ma_summary: "buy",
      ma_buy_count: 5,
      ma_sell_count: 2,
      ma_neutral_count: 3,
      indicators_summary: "buy",
      indicators_buy_count: 5,
      indicators_sell_count: 2,
      indicators_neutral_count: 6,
      overall_summary: "buy",
      overall_buy_count: 10,
      overall_sell_count: 4,
      overall_neutral_count: 9,
    },
    strategies: [
      {
        direction: "long",
        entry_condition: "Przebicie oporu",
        entry_price: 1.108,
        stop_loss: 1.104,
        tp1: 1.118,
        tp2: 1.125,
        confidence_pct: 72,
        risk_reward_ratio: 0.4,
      },
    ],
    strategy_skip_reason: null,
  };
}

function wsProgressMessages(id: string) {
  return [
    { id, status: "running", progress_pct: 15, current_step: "pobieranie", steps_completed: [], error_message: null },
    { id, status: "running", progress_pct: 40, current_step: "analiza techniczna", steps_completed: ["Pobieranie danych"], error_message: null },
    { id, status: "running", progress_pct: 65, current_step: "rozpoznawanie", steps_completed: ["Pobieranie danych", "Analiza techniczna"], error_message: null },
    { id, status: "running", progress_pct: 80, current_step: "agregacja", steps_completed: ["Pobieranie danych", "Analiza techniczna", "Rozpoznawanie formacji", "Analiza fundamentalna"], error_message: null },
    { id, status: "completed", progress_pct: 100, current_step: "", steps_completed: ["Pobieranie danych", "Analiza techniczna", "Rozpoznawanie formacji", "Analiza fundamentalna", "Agregacja sygnałów", "Generowanie strategii"], error_message: null },
  ];
}

/** Set up API route interception (HTTP + WebSocket) for a given page. */
export async function mockAnalysisApi(page: Page) {
  let requestedSymbol = "EURUSD";
  let requestedTimeframe = "H1";

  // Mock POST /api/v1/analysis
  await page.route("**/api/v1/analysis", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();

    const body = JSON.parse(route.request().postData() ?? "{}");
    requestedSymbol = body.symbol ?? "EURUSD";
    requestedTimeframe = body.timeframe ?? "H1";

    // Return 422 for obviously invalid symbols
    const validPattern = /^[A-Z0-9]{2,12}$/;
    if (!validPattern.test(requestedSymbol)) {
      return route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: "Nieprawidłowy symbol instrumentu" }) });
    }

    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ analysis_id: MOCK_ANALYSIS_ID, status: "pending" }),
    });
  });

  // Mock GET /api/v1/analysis/{id}
  await page.route(`**/api/v1/analysis/${MOCK_ANALYSIS_ID}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockReport(requestedSymbol, requestedTimeframe)),
    });
  });

  // Mock GET /api/v1/analysis/{id}/status
  await page.route(`**/api/v1/analysis/${MOCK_ANALYSIS_ID}/status`, async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: MOCK_ANALYSIS_ID,
        status: "completed",
        progress_pct: 100,
        current_step: "",
        steps_completed: ["Pobieranie danych", "Analiza techniczna", "Rozpoznawanie formacji", "Analiza fundamentalna", "Agregacja sygnałów", "Generowanie strategii"],
        error_message: null,
      }),
    });
  });

  // Mock WebSocket for progress updates
  await page.routeWebSocket("**/ws/analysis/**", (ws) => {
    const messages = wsProgressMessages(MOCK_ANALYSIS_ID);
    let i = 0;

    function sendNext() {
      if (i < messages.length) {
        ws.send(JSON.stringify(messages[i]));
        i++;
        if (i < messages.length) {
          setTimeout(sendNext, 150);
        }
      }
    }

    // Start sending progress after a short delay
    setTimeout(sendNext, 100);
  });
}

/** Extended test that automatically mocks the analysis API. */
export const test = base.extend<{ mockedPage: Page }>({
  mockedPage: async ({ page }, use) => {
    await mockAnalysisApi(page);
    await use(page);
  },
});
