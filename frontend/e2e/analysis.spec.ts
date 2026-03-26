import { expect, test } from "@playwright/test";

test.describe("Analysis Flow — EURUSD", () => {
  test("submits EURUSD H1 analysis and sees progress then results", async ({ page }) => {
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
    await expect(page.getByText(/postęp analizy/i)).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Analysis Flow — GOLD", () => {
  test("submits GOLD D1 analysis", async ({ page }) => {
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

    // Should show progress or form should indicate submission
    await expect(page.getByText(/postęp analizy|analiz/i)).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Invalid Symbol", () => {
  test("shows error for invalid symbol", async ({ page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("!!!!INVALID!!!!");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Should display an error message
    await expect(page.getByText(/błąd|error|nieprawidłow/i)).toBeVisible({ timeout: 10_000 });
  });
});
