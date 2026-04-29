import { expect } from "@playwright/test";
import { test, mockAnalysisApi } from "./fixtures";

test.describe("Analysis Flow — EURUSD (Forex)", () => {
  test("submits EURUSD H1 analysis, sees progress, then views results", async ({ mockedPage: page }) => {
    await page.goto("/");

    // Fill in the symbol
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    // Select from autocomplete if visible
    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    // Select timeframe
    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    // Submit
    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Progress indicator should appear
    await expect(page.getByRole("heading", { name: /postęp analizy/i })).toBeVisible({ timeout: 10_000 });

    // Wait for analysis result to appear
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Verify result contains key report sections
    await expect(page.getByText(/RSI|MACD|ADX/i).first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("heading", { name: /kontekst multi-timeframe/i })).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Trend długoterminowy/i)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Ramy czasowe/i).first()).toBeVisible({ timeout: 5_000 });

    // Verify candlestick chart renders canvas
    const chartFigure = page.getByRole("figure", { name: /wykres świecowy/i });
    await expect(chartFigure.locator("canvas").first()).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("Analysis Flow — GOLD (Commodity)", () => {
  test("submits GOLD D1 analysis, sees progress, then views results", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("GOLD");

    const option = page.getByRole("option", { name: /GOLD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("D1");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Should show progress
    await expect(page.getByRole("heading", { name: /postęp analizy/i })).toBeVisible({ timeout: 10_000 });

    // Wait for analysis result
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Verify candlestick chart renders canvas
    const chartFigure = page.getByRole("figure", { name: /wykres świecowy/i });
    await expect(chartFigure.locator("canvas").first()).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("Analysis Flow — US500 (Index)", () => {
  test("submits US500 H4 analysis, sees progress, then views results", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("US500");

    const option = page.getByRole("option", { name: /US500/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H4");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Should show progress
    await expect(page.getByRole("heading", { name: /postęp analizy/i })).toBeVisible({ timeout: 10_000 });

    // Wait for analysis result
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Verify candlestick chart renders canvas
    const chartFigure = page.getByRole("figure", { name: /wykres świecowy/i });
    await expect(chartFigure.locator("canvas").first()).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("Preset Selection — TradingView", () => {
  test("submits analysis with tradingview preset in request body", async ({ page }) => {
    await mockAnalysisApi(page);
    await page.goto("/");

    // Fill symbol
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    // Select TradingView preset
    const presetSelect = page.locator("#preset");
    await presetSelect.selectOption("tradingview");

    // Select timeframe
    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    // Intercept POST to verify preset in body
    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes("/api/v1/analysis") && req.method() === "POST"),
      page.getByRole("button", { name: /analiz/i }).click(),
    ]);

    const body = JSON.parse(request.postData() ?? "{}");
    expect(body.preset).toBe("tradingview");

    // Verify analysis completes
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });
  });
});

test.describe("Invalid Symbol", () => {
  test("shows error for invalid symbol", async ({ page }) => {
    await mockAnalysisApi(page);
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("INVALIDXYZ123");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Should display an error message
    await expect(page.getByText(/błąd|error|nieprawidłow/i)).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("ChartToolbar — widoczność warstw wykresu", () => {
  test("toolbar zawiera 4 przyciski z poprawnymi domyślnymi stanami", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Wszystkie 4 przyciski są widoczne — scope do sekcji wykresu (unikamy kolizji z innymi "Pivot Points" na stronie)
    const chartSection = page.getByLabel("Wykres", { exact: true });
    const emaButton = chartSection.getByRole("button", { name: "EMA" });
    const pivotButton = chartSection.getByRole("button", { name: "Pivot Points" });
    const fibButton = chartSection.getByRole("button", { name: "Fibonacci" });
    const patternsButton = chartSection.getByRole("button", { name: "Formacje" });

    await expect(emaButton).toBeVisible({ timeout: 5_000 });
    await expect(pivotButton).toBeVisible({ timeout: 5_000 });
    await expect(fibButton).toBeVisible({ timeout: 5_000 });
    await expect(patternsButton).toBeVisible({ timeout: 5_000 });

    // Domyślne stany: EMA i Formacje ON, Pivots i Fibonacci OFF
    await expect(emaButton).toHaveAttribute("aria-pressed", "true");
    await expect(patternsButton).toHaveAttribute("aria-pressed", "true");
    await expect(pivotButton).toHaveAttribute("aria-pressed", "false");
    await expect(fibButton).toHaveAttribute("aria-pressed", "false");
  });

  test("kliknięcie przycisku przełącza stan aria-pressed", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    const chartSection = page.getByLabel("Wykres", { exact: true });
    const emaButton = chartSection.getByRole("button", { name: "EMA" });
    await expect(emaButton).toHaveAttribute("aria-pressed", "true");

    // Kliknięcie wyłącza warstwę
    await emaButton.click();
    await expect(emaButton).toHaveAttribute("aria-pressed", "false");

    // Ponowne kliknięcie włącza
    await emaButton.click();
    await expect(emaButton).toHaveAttribute("aria-pressed", "true");
  });
});
