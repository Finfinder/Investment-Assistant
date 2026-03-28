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
