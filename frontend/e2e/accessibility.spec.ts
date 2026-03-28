import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockAnalysisApi } from "./fixtures";

test.describe("Accessibility — axe-core audit", () => {
  test("home page has no critical accessibility violations", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();

    expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
  });

  test("home page has no serious accessibility violations", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();

    expect(results.violations.filter((v) => v.impact === "serious")).toEqual([]);
  });
});

test.describe("Accessibility — keyboard navigation (form)", () => {
  test("can navigate form fields with Tab and submit with Enter", async ({ page }) => {
    await page.goto("/");

    // Tab to symbol input
    await page.keyboard.press("Tab");
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await expect(symbolInput).toBeFocused();

    // Type a symbol
    await symbolInput.fill("EURUSD");

    // Tab to preset select
    await page.keyboard.press("Tab");
    const presetSelect = page.locator("#preset");
    await expect(presetSelect).toBeFocused();

    // Tab to timeframe select
    await page.keyboard.press("Tab");
    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await expect(timeframeSelect).toBeFocused();

    // Tab to submit button
    await page.keyboard.press("Tab");
    const submitButton = page.getByRole("button", { name: /analiz/i });
    await expect(submitButton).toBeFocused();
  });

  test("combobox keyboard navigation with ArrowDown/Up/Enter/Escape", async ({ page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.click();
    await symbolInput.fill("EUR");

    // Wait for suggestions to appear
    const listbox = page.getByRole("listbox", { name: /sugestie/i });
    await expect(listbox).toBeVisible({ timeout: 5_000 });

    // ArrowDown should highlight first option
    await page.keyboard.press("ArrowDown");
    const options = listbox.getByRole("option");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");

    // ArrowDown again should move to next
    await page.keyboard.press("ArrowDown");

    // ArrowUp should go back
    await page.keyboard.press("ArrowUp");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");

    // Enter should select the option and close the listbox
    await page.keyboard.press("Enter");
    await expect(listbox).not.toBeVisible();

    // Input should contain selected value
    await expect(symbolInput).not.toHaveValue("EUR");
  });

  test("Escape closes combobox suggestions", async ({ page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.click();
    await symbolInput.fill("GOL");

    const listbox = page.getByRole("listbox", { name: /sugestie/i });
    await expect(listbox).toBeVisible({ timeout: 5_000 });

    // Escape should close suggestions
    await page.keyboard.press("Escape");
    await expect(listbox).not.toBeVisible();
  });
});

test.describe("Accessibility — report page structure", () => {
  test("tables have proper caption and section nav is accessible", async ({ page }) => {
    await mockAnalysisApi(page);
    await page.goto("/");

    // Submit a valid analysis to get report tables
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    // Wait for report to load
    await expect(page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()).toBeVisible({
      timeout: 60_000,
    });

    // Verify tables have sr-only captions
    const tables = page.locator("table");
    const tableCount = await tables.count();
    expect(tableCount).toBeGreaterThan(0);

    for (let i = 0; i < tableCount; i++) {
      const caption = tables.nth(i).locator("caption");
      if ((await caption.count()) > 0) {
        await expect(caption.first()).toHaveClass(/sr-only/);
      }
    }

    // Verify section navigation is keyboard accessible
    const sectionNav = page.getByRole("navigation", { name: /sekcje raportu/i });
    await expect(sectionNav).toBeVisible();

    const navButtons = sectionNav.getByRole("button");
    const navCount = await navButtons.count();
    expect(navCount).toBeGreaterThan(0);
  });

  test("report page has no critical/serious axe-core violations", async ({ page }) => {
    await mockAnalysisApi(page);
    await page.goto("/");

    // Submit analysis and wait for results
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    const submitButton = page.getByRole("button", { name: /analiz/i });
    await submitButton.click();

    await expect(page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()).toBeVisible({
      timeout: 60_000,
    });

    // Ensure the page is fully hydrated — html[lang] and <title> must be present
    await page.waitForFunction(
      () => document.documentElement.lang === "pl" && document.title.length > 0,
      { timeout: 10_000 },
    );

    // Scan the report DOM for a11y violations
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(violations).toEqual([]);
  });
});
