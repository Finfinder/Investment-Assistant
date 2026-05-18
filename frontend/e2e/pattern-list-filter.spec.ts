import { expect } from "@playwright/test";
import { test } from "./fixtures";

test.describe("PatternList - Filtrowanie po wiarygodności", () => {
  test.beforeEach(async ({ mockedPage: page }) => {
    await page.goto("http://localhost:3000");
    await page.waitForLoadState("networkidle");

    // Wpisz symbol
    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    // Wybierz option
    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    // Wybierz timeframe
    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    // Kliknij Analiz
    await page.getByRole("button", { name: /analiz/i }).click();

    // Czekaj na wyniki - pojawi się nagłówek z wynikami
    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // PatternList powinien być widoczny po wynikach - szukamy checkboxa
    const reliabilityCheckbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    await expect(reliabilityCheckbox).toBeVisible({
      timeout: 5_000,
    });
  });

  test("checkbox 'Pokaż tylko ★★+' jest domyślnie zaznaczony", async ({ mockedPage: page }) => {
    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    await expect(checkbox).toBeChecked();
  });

  test("checkbox domyślnie filtruje formacje - widoczne tylko ★★ i wyższe", async ({ mockedPage: page }) => {
    // Domyślnie checkbox zaznaczony - Doji (reliability: 1) powinno być ukryte
    const doji = page.getByRole("button", { name: /Doji/ });
    await expect(doji).not.toBeVisible();

    // Hammer i Ascending Triangle powinny być widoczne (reliability: 2)
    const hammer = page.getByRole("button", { name: /Hammer/ });
    const triangle = page.getByRole("button", { name: /Ascending Triangle/ });
    await expect(hammer).toBeVisible();
    await expect(triangle).toBeVisible();

    // Odzaznacz checkbox - wszystkie 3 formacje powinny być widoczne
    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    await checkbox.click();
    await page.waitForLoadState("networkidle");

    await expect(doji).toBeVisible();
  });

  test("odzaznaczenie i ponowne zaznaczenie checkboxa przełącza filtr", async ({ mockedPage: page }) => {
    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    const doji = page.getByRole("button", { name: /Doji/ });
    const hammer = page.getByRole("button", { name: /Hammer/ });
    const triangle = page.getByRole("button", { name: /Ascending Triangle/ });

    // Domyślnie zaznaczony - Doji ukryte
    await expect(doji).not.toBeVisible();

    // Odzaznacz - wszystkie formacje powinny być widoczne
    await checkbox.click();
    await page.waitForLoadState("networkidle");

    await expect(hammer).toBeVisible();
    await expect(triangle).toBeVisible();
    await expect(doji).toBeVisible();

    // Zaznacz ponownie - Doji powinno zniknąć
    await checkbox.click();
    await page.waitForLoadState("networkidle");

    await expect(doji).not.toBeVisible();
  });

  test("zmiana filtra resetuje state 'Rozwiń/Zwiń' i aktywną kategorię", async ({ mockedPage: page }) => {
    const candlestickTab = page.getByRole("button", { name: /Świecowe/ });
    await candlestickTab.click();

    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });

    // Odzaznacz checkbox - powinno zresetować expanded i kategorię
    await checkbox.click();
    await page.waitForLoadState("networkidle");

    // Po zmianie filtra aktywna kategoria wraca do "Wszystkie", więc widoczne są wzorce z innych kategorii
    const triangle = page.getByRole("button", { name: /Ascending Triangle/ });
    await expect(triangle).toBeVisible();

    // Przycisk "Pokaż wszystkie" powinien pokazywać liczbę według odfiltrowanej listy (3 zamiast 2)
    const expandButton = page.getByRole("button", { name: /Pokaż wszystkie/ });
    if (await expandButton.isVisible()) {
      // Tekst powinien zawierać "Pokaż wszystkie (3)"
      const text = await expandButton.textContent();
      expect(text).toContain("(3)");
    }
  });

  test("liczniki kategorii uwzględniają filtr wiarygodności", async ({ mockedPage: page }) => {
    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    const candlestickTab = page.getByRole("button", { name: /Świecowe/ });

    // Domyślnie checkbox zaznaczony - Świecowe (1) bo Doji (reliability:1) jest odfiltrowany
    const defaultText = await candlestickTab.textContent();
    expect(defaultText).toMatch(/Świecowe \(1\)/);

    // Odzaznacz - Świecowe (2) bo Doji wraca
    await checkbox.click();
    await page.waitForLoadState("networkidle");

    const unfilteredText = await candlestickTab.textContent();
    expect(unfilteredText).toMatch(/Świecowe \(2\)/);
  });

  test("checkbox posiada dostęp dla czytników ekranu", async ({ mockedPage: page }) => {
    const checkbox = page.getByRole("checkbox", { name: /Pokaż tylko ★★\+/ });
    const label = page.getByText("Pokaż tylko ★★+");

    // Checkbox i label powinny być powiązane
    await expect(checkbox).toHaveAttribute("aria-label", /Pokaż tylko ★★\+/);
    await expect(label).toBeVisible();
  });
});

test.describe("PatternList - Pusty stan dla filtra reliability", () => {
  test("pokazuje komunikat pustego stanu, gdy brak formacji ★★+", async ({ mockedPage: page }) => {
    await page.route("**/api/v1/analysis/mock-analysis-id", async (route) => {
      const now = new Date().toISOString();
      const report = {
        symbol: "EURUSD",
        timeframe: "H1",
        timestamp: now,
        instrument_type: "forex",
        timeframe_context: {
          pivot_points_timeframe: "D1",
          pattern_scanner_timeframes: ["D1", "H1", "M15"],
          long_term_trend_label: "weekly",
        },
        ohlcv_data: [
          {
            timestamp: now,
            open: 1.1,
            high: 1.102,
            low: 1.099,
            close: 1.101,
            volume: 1000,
          },
        ],
        technical_indicators: [
          { name: "RSI(14)", value: 55.3, signal: "neutral" },
        ],
        moving_averages: [
          { period: 10, sma_value: 1.105, sma_signal: "buy", ema_value: 1.106, ema_signal: "buy" },
        ],
        pivot_points: [
          { type: "classic", pp: 1.105, s1: 1.1, s2: 1.095, s3: 1.09, r1: 1.11, r2: 1.115, r3: 1.12 },
        ],
        patterns: [
          {
            pattern_type: "Doji",
            confidence: 0.55,
            description: "Świeca Doji sygnalizująca niepewność rynku.",
            location: "current",
            bullish: false,
            category: "candlestick",
            timeframe: "H1",
            detected_at_index: 25,
            detected_at_timestamp: now,
            relevance_score: 0.45,
            target_price: null,
            indication: "Niedźwiedź",
            reliability: 1,
            detailed_description: "Doji pojawia się, gdy otwarcie i zamknięcie ceny są bliskie sobie.",
          },
        ],
        pattern_scanner_results: [
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
              detected_at_timestamp: now,
              relevance_score: 0.45,
              target_price: null,
              indication: "Niedźwiedź",
              reliability: 1,
              detailed_description: "Doji pojawia się, gdy otwarcie i zamknięcie ceny są bliskie sobie.",
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
          ma_buy_count: 1,
          ma_sell_count: 0,
          ma_neutral_count: 0,
          indicators_summary: "neutral",
          indicators_buy_count: 0,
          indicators_sell_count: 0,
          indicators_neutral_count: 1,
          overall_summary: "neutral",
          overall_buy_count: 1,
          overall_sell_count: 0,
          overall_neutral_count: 1,
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

      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    });

    await page.goto("http://localhost:3000");
    await page.waitForLoadState("networkidle");

    const symbolInput = page.getByRole("combobox", { name: /symbol/i });
    await symbolInput.fill("EURUSD");

    const option = page.getByRole("option", { name: /EURUSD/i });
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click();
    }

    const timeframeSelect = page.getByRole("combobox", { name: /timeframe/i });
    await timeframeSelect.selectOption("H1");

    await page.getByRole("button", { name: /analiz/i }).click();

    await expect(
      page.getByRole("heading", { name: /podsumowanie|wskaźnik|strategi/i }).first()
    ).toBeVisible({ timeout: 60_000 });

    // Checkbox domyślnie zaznaczony - pusty stan powinien być widoczny od razu
    await expect(
      page.getByText("Brak formacji o wiarygodności ★★ i wyższej w tej kategorii")
    ).toBeVisible();
  });
});
