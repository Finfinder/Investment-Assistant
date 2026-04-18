import { expect } from "@playwright/test";
import { test, mockAnalysisApi } from "./fixtures";

test.describe("PatternDetailModal", () => {
  test.beforeEach(async ({ mockedPage: page }) => {
    await mockAnalysisApi(page);
  });

  test("otwiera modal po kliknięciu formacji i wyświetla pola reliability", async ({
    mockedPage: page,
  }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    await page.getByRole("button", { name: /analiz/i }).click();

    // Czekamy na wyniki
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Klikamy pierwszy wiersz formacji
    const patternRow = page.getByRole("button", { name: /Hammer/i }).first();
    await expect(patternRow).toBeVisible({ timeout: 5_000 });
    await patternRow.click();

    // Modal powinien być widoczny
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 3_000 });

    // Weryfikujemy pola reliability
    await expect(dialog.getByText("★★")).toBeVisible();
    await expect(dialog.getByText("Odwrót bycza")).toBeVisible();
    await expect(dialog.getByText(/Formacja młota pojawia się/)).toBeVisible();
  });

  test("zamyka modal klawiszem Escape", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    await page.getByRole("combobox", { name: /timeframe/i }).selectOption("H1");
    await page.getByRole("button", { name: /analiz/i }).click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    const patternRow = page.getByRole("button", { name: /Hammer/i }).first();
    await expect(patternRow).toBeVisible({ timeout: 5_000 });
    await patternRow.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 3_000 });

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible({ timeout: 2_000 });
  });

  test("zamyka modal przyciskiem X", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    await page.getByRole("combobox", { name: /timeframe/i }).selectOption("H1");
    await page.getByRole("button", { name: /analiz/i }).click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    const patternRow = page.getByRole("button", { name: /Hammer/i }).first();
    await expect(patternRow).toBeVisible({ timeout: 5_000 });
    await patternRow.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 3_000 });

    await dialog.getByRole("button", { name: /zamknij/i }).click();
    await expect(dialog).not.toBeVisible({ timeout: 2_000 });
  });

  test("modal ma atrybut role=dialog i aria-modal=true (WCAG)", async ({ mockedPage: page }) => {
    await page.goto("/");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    await page.getByRole("combobox", { name: /timeframe/i }).selectOption("H1");
    await page.getByRole("button", { name: /analiz/i }).click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    const patternRow = page.getByRole("button", { name: /Hammer/i }).first();
    await expect(patternRow).toBeVisible({ timeout: 5_000 });
    await patternRow.click();

    const dialogEl = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(dialogEl).toBeVisible({ timeout: 3_000 });
  });
});
