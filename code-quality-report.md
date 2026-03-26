# Raport Jakości Kodu - Investment Assistant (Rewizja 2)

## Przegląd

| Pole | Wartość |
|---|---|
| Repozytorium | Investment Assistant |
| Typ repozytorium | Monorepo |
| Data | 2026-03-27 |
| Analizowane warstwy/aplikacje | Backend (`backend/`), Frontend (`frontend/`) |
| Poprzednia rewizja | 2026-03-26 (67 ustaleń, 5 krytycznych — wszystkie 5 zaadresowane) |

## Podsumowanie wykonawcze

Ponowna analiza po wdrożeniu poprawek z pierwszego code review. Z 5 pierwotnych ustaleń krytycznych **wszystkie zostały zaadresowane**: CORS ograniczony do konkretnych metod/nagłówków, slowapi aktywowany na endpointach `/analysis` i `/market-data`, `FredSource` wykorzystuje `asyncio.to_thread()`, AnalysisForm posiada kompletny ARIA combobox z nawigacją klawiaturową, testy E2E przechodzą. Walidacja symboli i periods została scentralizowana w `validators.py`, a `Semaphore` ogranicza współbieżne analizy.

W tej rewizji zidentyfikowano **5 nowych problemów krytycznych**: (1) parametr `analysis_id` w GET endpointach nie jest walidowany jako UUID — umożliwia injection próby, (2) stan analiz przechowywany in-memory w `TTLCache` blokuje skalowanie horyzontalne, (3) klasyfikacja symboli rozproszona w 5+ plikach — mina utrzymywalności, (4) canvas wykresu świecowego niewidoczny dla screen readerów, (5) frontend pozbawiony jakichkolwiek testów jednostkowych.

Ogólna jakość poprawiła się (67 → 51 ustaleń), ale nowe krytyczne ustalenia wymagają natychmiastowej uwagi. Rate limiting nie obejmuje jeszcze endpointów `/technical-analysis`, `/patterns` i `/fundamental-analysis`, które również wywołują kosztowne API zewnętrzne.

---

## Ustalenia według warstwy/aplikacji

### Backend (`backend/`)

#### Martwy kod

| # | Istotność | Typ | Lokalizacja | Opis |
|---|---|---|---|---|
| 1 | 🟡 Ważne | Martwa logika scoringowa | `backend/app/modules/fundamental_analysis/indices.py:91` | `_score_inflation()` zawsze zwraca `(0.0, opis)` niezależnie od wartości wejściowych. Każda gałąź warunkowa (cpi is None, rate is not None, fallback) zwraca 0.0 — scoring inflacji nie wpływa nigdy na wynik analizy indeksów. |
| 2 | 🟡 Ważne | Nieużywane metody | `backend/app/modules/fundamental_analysis/data_sources/fmp_source.py:64` | `fetch_treasury_rates()`, `fetch_economic_indicator()`, `fetch_economic_calendar()` na `FmpEconomicSource` — nigdy wywoływane z kodu produkcyjnego. |
| 3 | 🟡 Ważne | Nieużywane metody | `backend/app/modules/data_acquisition/providers/fmp_provider.py:155` | `fetch_economic_calendar()`, `fetch_cot_reports()`, `fetch_treasury_rates()` na `FMPProvider` — zdefiniowane ale nigdy wywoływane. Duplikują funkcjonalność z `fmp_source.py`. |
| 4 | 🟡 Ważne | Nieużywany eksport | `frontend/src/lib/api.ts:39` | `getAnalysisStatus()` eksportowana, ale nigdy nieimportowana. Jedynie `triggerAnalysis`, `getAnalysis` i `connectAnalysisWebSocket` są używane. |
| 5 | 🟢 Nice to Have | Moduł nigdy nie czytany | `backend/app/core/database.py:41` | `_engine` zapisywany w zmiennej modułowej, ale nigdy odczytywany po przypisaniu — brak `dispose()` przy shutdown. |
| 6 | 🟢 Nice to Have | Metoda tylko w testach | `backend/app/modules/fundamental_analysis/data_sources/fred_source.py:98` | `fetch_multiple()` wywoływana wyłącznie w testach, nigdy z kodu produkcyjnego. |
| 7 | 🟢 Nice to Have | Metoda tylko w testach | `backend/app/modules/data_acquisition/cache.py:42` | `InMemoryCache.invalidate()` wywoływana wyłącznie w testach. |
| 8 | 🟢 Nice to Have | Nieużywane metody Protocol | `backend/app/modules/data_acquisition/interfaces.py:29` | `get_supported_symbols()` i `is_available()` na `DataProvider` Protocol — zaimplementowane we wszystkich providerach, ale nigdy wywoływane z kodu produkcyjnego. |

#### Duplikacje

| # | Istotność | Typ | Lokalizacje | Opis | Rekomendacja |
|---|---|---|---|---|---|
| 1 | � Krytyczne | Rozproszona klasyfikacja symboli | `backend/app/core/instrument_classifier.py`, `backend/app/modules/data_acquisition/providers/yfinance_provider.py:12`, `twelve_data_provider.py:53`, `fmp_provider.py:24`, `fmp_source.py` | Logika mapowania i klasyfikacji symboli rozproszona w 5+ plikach. Każdy provider utrzymuje własny słownik mapowań z nakładającymi się symbolami. Zmiana klasyfikacji instrumentu wymaga synchronicznej edycji wielu plików — mina utrzymywalności. | Stworzyć centralny rejestr instrumentów w `app.core` z kanonicznymi symbolami i mapowaniami per-provider jako transformerami. |
| 2 | 🟡 Ważne | Zduplikowane obliczanie ATR | `backend/app/modules/pattern_recognition/iki_detector.py:140`, `backend/app/modules/strategy_generator/sl_tp_calculator.py:12` | ATR obliczane niezależnie w 2 modułach z różnymi sygnaturami (numpy arrays vs `OHLCVData` list). | Import-linter wymusza niezależność modułów — wyekstrahować ATR do `app.core` jako shared utility lub zaakceptować duplikację jako trade-off granic modułowych. |
| 3 | 🟡 Ważne | Zduplikowany regex cen | `backend/app/modules/strategy_generator/entry_calculator.py:129`, `backend/app/modules/strategy_generator/sl_tp_calculator.py:32` | Oba parsują ceny S/R z opisów wzorców podobnym regexem. | Połączyć w jedną utility w module `strategy_generator`. Docelowo zastąpić regex-on-description strukturalnym polem w modelu. |
| 4 | 🟡 Ważne | Zduplikowana konwersja period | `backend/app/modules/data_acquisition/providers/fmp_provider.py:195`, `yfinance_provider.py:73`, fragmentarycznie w `twelve_data_provider.py` | `_period_to_days()` z identyczną logiką w wielu providerach. | Wyekstrahować do utils modułu `data_acquisition`. |
| 5 | 🟡 Ważne | Niezależne rate limitery FMP | `backend/app/modules/data_acquisition/providers/fmp_provider.py:63`, `backend/app/modules/fundamental_analysis/data_sources/fmp_source.py:29` | `DAILY_RATE_LIMIT=250` zdefiniowany w obu plikach z osobnymi instancjami `DailyRateLimiter`. Przy równoczesnym użyciu obu łącznie mogą przekroczyć faktyczny limit planu FMP (250/dzień). | Wyekstrahować współdzielony `DailyRateLimiter` do `app.core` z jednym globalnym licznikiem. |
| 6 | 🟢 Nice to Have | Zduplikowane TIMEFRAME_MAP | 3 pliki providerów | Każdy provider definiuje własną mapę timeframe → format API. | Akceptowalne — specyficzne formaty per provider (np. `1h` vs `60min` vs `1hour`). |
| 7 | 🟢 Nice to Have | Zduplikowana konstrukcja DataFrame | `backend/app/modules/technical_analysis/indicators.py`, `moving_averages.py` | Konwersja `OHLCVData` → pandas DataFrame duplikowana w obu plikach. | Wyekstrahować helper `ohlcv_to_dataframe()` do `technical_analysis._helpers`. |

#### Obszary do usprawnień

| # | Istotność | Kategoria | Lokalizacja | Opis | Rekomendacja |
|---|---|---|---|---|---|
| 1 | 🔴 Krytyczne | Walidacja wejścia | `backend/app/api/v1/analysis.py:66,77` | `analysis_id` jako parametr ścieżki w GET `/analysis/{analysis_id}` i `/analysis/{analysis_id}/status` jest gołym `str` bez walidacji formatu UUID. Złośliwe wartości trafiają do lookup w `analysis_tasks` (TTLCache) i `_analysis_results`. Brak walidacji w endpoincie WebSocket `/ws/analysis/{analysis_id}`. | Dodać walidację UUID4 do parametru `analysis_id` np. przez Pydantic `Path(pattern=...)` lub dedykowany validator w `validators.py`. |
| 2 | 🔴 Krytyczne | Skalowalność | `backend/app/api/v1/analysis.py:53,55` | Stan analiz (`_analysis_results`, `_background_tasks`) i status (`analysis_tasks` w `pipeline.py`) przechowywany w pamięci procesu jako `TTLCache`/`dict`. Blokuje: (a) skalowanie horyzontalne — wiele instancji nie współdzieli stanu, (b) restart procesu traci wyniki, (c) TTL w `_background_tasks` może usunąć referencję `asyncio.Task` przed zakończeniem. | Krótkoterminowo: wystarczające dla MVP z jedną instancją. Średnioterminowo: przenieść stan do Redis lub bazy danych. Rozważyć Celery/ARQ dla task queue. |
| 3 | 🟡 Ważne | Bezpieczeństwo | `backend/app/api/v1/analysis.py:89` | WebSocket endpoint `/ws/analysis/{analysis_id}` — brak jakiejkolwiek autentykacji. Dowolny klient może subskrybować aktualizacje dowolnej analizy znając `analysis_id`. | Dodać token-based auth (np. query param `?token=`) weryfikowany przy `websocket.accept()`. |
| 4 | 🟡 Ważne | Bezpieczeństwo | Endpointy POST | Rate limiting aktywny tylko na `/analysis` (10/min) i `/market-data` (30/min). Endpointy POST `/technical-analysis`, `/patterns`, `/fundamental-analysis` nie mają rate limitingu — wywołują kosztowne API zewnętrzne i ciężkie obliczenia. | Dodać `@limiter.limit()` do pozostałych endpointów POST. |
| 5 | 🟡 Ważne | Niezależne rate limitery | `backend/app/modules/data_acquisition/providers/fmp_provider.py`, `fmp_source.py` | `FMPProvider` i `FmpEconomicSource` mają niezależne instancje `DailyRateLimiter` z `DAILY_RATE_LIMIT=250`. Przy równoczesnym użyciu obu (pipeline fundamental + data acquisition) mogą łącznie przekroczyć dzienny limit FMP API. | Współdzielić jedną instancję rate limitera między oboma klientami FMP. |
| 6 | 🟡 Ważne | Lifecycle | `backend/app/main.py`, `backend/app/core/database.py` | Brak ASGI lifespan event handler. Silnik SQLAlchemy (`_engine`) nigdy nie jest jawnie `dispose()`'owany przy shutdown. `lru_cache` w `market_data.py` nie jest czyszczony. Potencjalny resource leak przy graceful shutdown. | Dodać `@asynccontextmanager` lifespan handler w `create_app()` z `engine.dispose()` i czyszczeniem cache. |
| 7 | 🟡 Ważne | Wydajność | 5 call sites w modułach | `httpx.AsyncClient` tworzony per-request (new → request → close). Brak reużycia connection pool, TLS handshake przy każdym zapytaniu. | Stworzyć app-scoped `httpx.AsyncClient` z lifespan management (open w startup, close w shutdown). |
| 8 | 🟡 Ważne | Złożoność | `backend/app/modules/pattern_recognition/iki_detector.py` | `_find_iki()` ~65 linii z 4 poziomami zagnieżdżenia. Trudna do testowania jednostkowego i utrzymania. | Wyekstrahować warunki walidacji i logikę scoringową do mniejszych metod. |
| 9 | 🟡 Ważne | Złożoność | `backend/app/modules/pipeline.py:111` | `AnalysisPipeline.run()` ~70 linii z 6 sekwencyjnymi etapami, każdy z indywidualnym try/except. | Wyekstrahować każdy krok do osobnej metody. Rozważyć step runner pattern z kolekcją błędów. |
| 10 | 🟡 Ważne | Spójność | `backend/app/api/v1/fundamental.py:31,55` | Komunikaty błędów w języku polskim: `"Nierozpoznany instrument: ..."`, `"Blad analizy fundamentalnej dla ..."`. Reszta API używa angielskiego (`"Invalid symbol format"`, `"Analysis not found"`). | Ujednolicić język komunikatów błędów w całym API. |
| 11 | 🟡 Ważne | Obsługa błędów | `backend/app/api/v1/fundamental.py:55` | `raise HTTPException(...) from None` ucina łańcuch wyjątków. W trybie debug/logach trace nie pokaże pierwotnej przyczyny awarii analizy fundamentalnej. | Usunąć `from None` — pozwolić na propagację łańcucha wyjątków (logowany przez `logger.exception` powyżej). |
| 12 | 🟢 Nice to Have | Złożoność | `backend/app/modules/pattern_recognition/chart_patterns.py` | Rozbudowane wielogałęziowe drzewo klasyfikacji wzorców (Head & Shoulders, Triangles, Wedges itp.). Złożone, ale domena tego wymaga. | Akceptowalne — domena ze swej natury złożona. Dokumentacja inline jest wystarczająca. |
| 13 | 🟢 Nice to Have | Spójność | `backend/app/modules/fundamental_analysis/data_sources/fmp_source.py`, `fmp_provider.py` | Niespójna konwencja nazewnictwa: `FMPProvider` vs `FmpEconomicSource`, `FMP_BASE_URL` vs `BASE_URL`. | Ustandaryzować konwencje nazewnictwa — preferować `Fmp` (PascalCase camelCase hybrid). |
| 14 | 🟢 Nice to Have | Bug | Providery `twelve_data_provider.py`, `yfinance_provider.py` | Parsowanie period ignoruje jednostkę `"m"` (miesiąc). `"6m"` nie zostanie poprawnie skonwertowane na liczbę dni — wynik może być zaskakujący. | Obsłużyć `"m"` → ~30 dni w `_period_to_days()`. |

---

### Frontend (`frontend/`)

#### Martwy kod

| # | Istotność | Typ | Lokalizacja | Opis |
|---|---|---|---|---|
| 1 | 🟡 Ważne | Nieużywany eksport | `frontend/src/lib/api.ts:39` | `getAnalysisStatus()` eksportowana, ale nigdy nieimportowana w codebase. Jedynie `triggerAnalysis`, `getAnalysis` i `connectAnalysisWebSocket` są używane. |
| 2 | 🟢 Nice to Have | Nieużywana zmienna CSS | `frontend/src/app/globals.css:13` | Zmienna CSS `--warning` zdefiniowana, ale nigdy niereferencjonowana w żadnej klasie komponentu. |
| 3 | 🟢 Nice to Have | Martwy font loading | `frontend/src/app/layout.tsx:5` | `geistSans` i `geistMono` ładowane via `next/font/local`, zmienne CSS `--font-geist-sans` i `--font-geist-mono` ustawiane na `<body>`, ale nigdy niereferencjonowane w `globals.css`, `tailwind.config.ts` ani żadnym komponencie. Font files pobierane na darmo. |
| 4 | 🟢 Nice to Have | Nieużywane eksporty typów | `frontend/src/types/index.ts` | `InstrumentType`, `PivotType`, `AnalysisStatusType`, `Direction` — eksportowane, ale nigdy bezpośrednio importowane. Używane jedynie wewnętrznie w definicjach interfejsów. |

#### Duplikacje

| # | Istotność | Typ | Lokalizacje | Opis | Rekomendacja |
|---|---|---|---|---|---|
| 1 | 🟡 Ważne | Zduplikowane formatery | `frontend/src/components/IndicatorTable/shared.tsx:26`, `frontend/src/components/Fundamental/FundamentalPanel.tsx:53` | `formatValue()` i `formatIndicatorValue()` — podobne, oba formatują liczby z `.toFixed(4)` i obsługują null/undefined. | Rozszerzyć wspólny `formatValue` o obsługę `string` i reużywać w FundamentalPanel. |
| 2 | 🟡 Ważne | Zduplikowany gauge visual | `frontend/src/components/Fundamental/FundamentalPanel.tsx:34`, `frontend/src/components/SignalSummary/SignalGauge.tsx:41` | `ScoreBar` i `SignalGauge` — niemal identyczny gradient bar UI z absolutnie pozycjonowanym wskaźnikiem kołowym. | Wyekstrahować reużywalny komponent `<GaugeBar position={number} color={string} />`. |
| 3 | 🟢 Nice to Have | Kolizja nazw stałych | `frontend/src/components/PivotPoints/PivotTable.tsx`, `FundamentalPanel.tsx` | `TYPE_LABELS` zdefiniowane w obu plikach z różnymi wartościami — potencjalne zamieszanie przy imporcie. | Nadać unikalne nazwy lub przenieść do osobnych plików konfiguracyjnych. |
| 4 | 🟢 Nice to Have | Powtórzony wrapper karty | 11 komponentów w `frontend/src/components/` | Wzorzec `rounded-xl border border-border bg-card` powtórzony w 11 komponentach. | Wyekstrahować `<Card>` wrapper lub klasę Tailwind `@apply`. |
| 5 | 🟢 Nice to Have | Zduplikowany styling formularza | `frontend/src/components/AnalysisForm.tsx` | Klasy input (`rounded-lg border border-border bg-card px-4 py-2.5...`) powtórzone na `<input>` i `<select>`. | Wyekstrahować wspólną klasę Tailwind. |

#### Obszary do usprawnień

| # | Istotność | Kategoria | Lokalizacja | Opis | Rekomendacja |
|---|---|---|---|---|---|
| 1 | 🔴 Krytyczne | Accessibility | `frontend/src/components/Chart/CandlestickChart.tsx:213` | Canvas wykresu świecowego niewidoczny dla screen readerów. Kontener ma `aria-label="Wykres świecowy"`, ale canvas nie posiada żadnej tekstowej alternatywy z danymi. Wykres to kluczowy element aplikacji — w całości niedostępny dla użytkowników z niepełnosprawnościami wzroku. | Dodać `role="img"` z `aria-label` opisującym zakres danych i trend, lub ukryty `<table>` z danymi OHLCV jako alternatywę. |
| 2 | 🔴 Krytyczne | Pokrycie testami | `frontend/` | **Zero testów jednostkowych** dla komponentów React, funkcji utility, logiki WebSocket. Jedynie 3 testy E2E (Playwright). Każda zmiana frontendu jest de facto niestestowana. | Skonfigurować Vitest + React Testing Library. Dodać testy dla: `api.ts`, `formatValue`, `confidenceBarClass`, `CandlestickChart` (rendering), `AnalysisForm` (interakcje). |
| 3 | 🟡 Ważne | Bezpieczeństwo typów | `frontend/src/components/Chart/CandlestickChart.tsx:192` | `createSeriesMarkers(series as any, markers as any)` — podwójny cast `as any` z eslint-disable. Całkowicie omija type checking. | Zbadać typy `lightweight-charts` v5.1 dla `createSeriesMarkers`. Stworzyć wąsko typowany wrapper. |
| 4 | 🟡 Ważne | SRP / Złożoność | `frontend/src/app/page.tsx` | `HomePage` to 210+ linii zarządzających: maszyną stanów, wywołaniami API, scroll spy, nawigacją sekcji, obsługą błędów i renderowaniem layoutu raportu. | Wyekstrahować: (1) `useAnalysis` hook, (2) `<ReportView>` komponent, (3) `<StickyNav>` komponent. |
| 5 | 🟡 Ważne | Bezpieczeństwo | `frontend/next.config.mjs` | Brak nagłówków bezpieczeństwa HTTP: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`. Konfiguracja zawiera wyłącznie `output: "standalone"`. | Dodać sekcję `headers()` w next.config.mjs z nagłówkami bezpieczeństwa. Nginx może je ustawiać, ale defense-in-depth wymaga obu warstw. |
| 6 | 🟡 Ważne | Obsługa błędów | `frontend/src/lib/api.ts:54` | WebSocket `onmessage` cicho połyka błędy parsowania JSON z pustym `catch {}`. Zniekształcone lub nieoczekiwane wiadomości serwera są gubione bez logowania. | Logować błąd w development. Rozważyć wywołanie `onError`. |
| 7 | 🟡 Ważne | Resilience | Cały frontend | Brak `React.ErrorBoundary` w drzewie komponentów. Uncaught render error w dowolnym komponencie (np. `CandlestickChart`) powoduje białą stronę bez informacji zwrotnej. | Dodać Error Boundary na poziomie layoutu i/lub wokół każdej sekcji raportu. |
| 8 | 🟡 Ważne | Pokrycie testami | `frontend/e2e/analysis.spec.ts` | 3 testy E2E weryfikują nawigację i formularz, ale nie sprawdzają zawartości raportu (poprawność wyświetlanych danych, obecność sekcji, wyświetlanie wskaźników). | Rozszerzyć E2E o asercje na zawartość raportu: obecność sekcji, poprawne wartości wskaźników, renderowanie wykresu. |
| 9 | 🟢 Nice to Have | Bezpieczeństwo | `frontend/src/lib/api.ts` | Konstrukcja WebSocket URL — brak walidacji pochodzenia przy budowaniu absolute URL. | Dodać walidację, że URL wskazuje na oczekiwany host. |
| 10 | 🟢 Nice to Have | Spójność | Wiele komponentów | Niespójne traktowanie pustego stanu — niektóre komponenty wyświetlają `"Brak danych"`, inne zwracają `null`, jeszcze inne pustą tabelę. | Ujednolicić podejście; wyekstrahować `<EmptyState>`. |
| 11 | 🟢 Nice to Have | Accessibility | `frontend/src/components/Section.tsx` | Przycisk nawigacji sekcji bez `type="button"` — wewnątrz `<form>` może triggerować submit. | Dodać `type="button"`. |
| 12 | 🟢 Nice to Have | Wydajność | Komponenty list i tabel | Żaden komponent prezentacyjny nie używa `React.memo`. Scroll spy w `page.tsx` powoduje re-render wszystkich sub-komponentów przy zmianie `activeSection`. | Opakować stabilne komponenty w `React.memo`. |
| 13 | 🟢 Nice to Have | Wydajność | `frontend/src/components/Chart/CandlestickChart.tsx` | Zmiana danych price line (pivot points, Fibonacci) powoduje pełny rebuild wykresu zamiast inkrementalnej aktualizacji. | Memoizować dane wejściowe i aktualizować wyłącznie zmienione price lines. |
| 14 | 🟢 Nice to Have | Niezawodność | Frontend | Brak runtime walidacji odpowiedzi API. Jeśli backend zwróci nieoczekiwaną strukturę, frontend przyjmie ją bezkrytycznie. | Rozważyć Zod schema do walidacji krytycznych odpowiedzi API. |

---

## Obserwacje architektoniczne

### Pozytywne aspekty

1. **Egzekwowane granice modułów**: Import-linter z trzema kontraktami (niezależność modułów domenowych, core nie importuje z modules/api, modules nie importuje z api) zapewnia czystą separację. Brak cykli zależności.
2. **Modularna struktura backendu**: Sześć niezależnych modułów domenowych z jasno zdefiniowanymi odpowiedzialnościami. Kierunek zależności `api → modules → core` poprawny.
3. **Wzorzec Fallback Chain**: Eleganckie rozwiązanie dla odporności data acquisition — automatyczny fallback między providerami (YFinance → TwelveData → FMP). `build_fallback_chain()` scentralizowane w module.
4. **Scentralizowana walidacja**: `validators.py` z jednym kanonicznym `SYMBOL_PATTERN` i `PERIOD_PATTERN` używanym przez wszystkie endpointy — eliminuje niespójności z rewizji 1.
5. **Zaawansowany tooling jakości**: Ruff (szerokie reguły), mypy (strict), import-linter, pytest (269 testów passing), ESLint + next lint (clean), next build (sukces).
6. **Rate limiting i concurrency control**: `slowapi` aktywny na kluczowych endpointach, `Semaphore` chroni przed resource exhaustion.

### Obszary wymagające uwagi

1. **In-memory state blokuje skalowanie**: `TTLCache` dla wyników analiz i `dict` dla statusów — restart procesu = utrata danych, wiele instancji = niespójny stan. Wystarczające dla MVP, ale wymagające migracji do Redis/DB przed produkcyjnym deploy.
2. **Brak ASGI lifespan**: Brak jawnego cyklu życia aplikacji — silnik SQLAlchemy nigdy nie jest `dispose()`'owany, httpx klients nie są zamykani, `lru_cache` nie jest czyszczona. Resource leak przy graceful shutdown.
3. **Sprzężenie przez strings**: Moduł `strategy_generator` wyciąga dane z `PatternDetection.description` przez regex zamiast structured fields — kruche i podatne na ciche awarie.
4. **Rozproszona klasyfikacja symboli**: 5+ plików z mapowaniami symboli — największe ryzyko utrzymywalności. Dodanie nowego instrumentu wymaga edycji wielu plików bez kontroli kompletności.
5. **Frontend — brak testów jednostkowych**: Jedyny safety net to 3 testy E2E. Brak testów dla business logic (formatery, transformery), komponentów React, logiki WebSocket. Wysoki risk regresji.
6. **Brak nagłówków bezpieczeństwa**: `next.config.mjs` nie definiuje żadnych nagłówków HTTP (CSP, X-Frame-Options itp.). Nginx może je ustawiać, ale defense-in-depth wymaga obu warstw.
7. **Brak Error Boundary**: Uncaught render error w dowolnym komponencie (np. przy malformed API response) powoduje białą stronę bez fallback UI.

### Poprawy od rewizji 1

Poniższe ustalenia krytyczne i ważne z rewizji 1 zostały zaadresowane:

| Rewizja 1 # | Istotność | Opis | Status |
|---|---|---|---|
| Usp. #1 | 🔴 Krytyczne | CORS `allow_methods=["*"]`, `allow_headers=["*"]` | ✅ Ograniczone do `GET`, `POST`, `OPTIONS` / `Content-Type` |
| Usp. #2 | 🔴 Krytyczne | Brak rate limitingu — `slowapi` nieużywany | ✅ Active na `/analysis` (10/min) i `/market-data` (30/min) |
| Usp. #3 | 🔴 Krytyczne | FredSource blokujące I/O w async loop | ✅ `asyncio.to_thread()` zastosowany |
| FE Usp. #1 | 🔴 Krytyczne | AnalysisForm bez ról ARIA, E2E zepsute | ✅ Pełny ARIA combobox + klawiatura + E2E fix |
| FE Usp. #2 | 🔴 Krytyczne | Brak nawigacji klawiaturowej w autocomplete | ✅ ArrowUp/Down, Enter, Escape, aria-activedescendant |
| Dup. #1 | 🟡 Ważne | `SYMBOL_PATTERN` zduplikowany 4× z niespójnością | ✅ Scentralizowany w `validators.py` |
| Usp. #4 | 🟡 Ważne | Brak semaphore na współbieżne analizy | ✅ `_analysis_semaphore` z limitem 5 |
| Usp. #9 | 🟡 Ważne | Globalny mutowalny stan w `market_data.py` | ✅ Zamieniony na `@lru_cache` |
| Usp. #11 | 🟡 Ważne | Brak walidacji period | ✅ `validate_period()` w `validators.py`, użyte we wszystkich endpointach |
| Dup. #5 | 🟡 Ważne | FallbackChain duplikowana w pipeline i market_data | ✅ `build_fallback_chain()` scentralizowany |
| MK #10 | 🟡 Ważne | slowapi jako nieużywana zależność | ✅ Aktywnie używany |

---

## Podsumowanie

| Kategoria | 🔴 Krytyczne | 🟡 Ważne | 🟢 Nice to Have | Razem |
|---|---|---|---|---|
| Martwy kod | 0 | 4 | 4 | 8 |
| Duplikacje | 1 | 4 | 2 | 7 |
| Usprawnienia Backend | 2 | 9 | 3 | 14 |
| Martwy kod Frontend | 0 | 1 | 3 | 4 |
| Duplikacje Frontend | 0 | 2 | 3 | 5 |
| Usprawnienia Frontend | 2 | 5 | 6 | 13 |
| **Razem** | **5** | **25** | **21** | **51** |

### Porównanie z rewizją 1

| Metryka | Rewizja 1 | Rewizja 2 | Zmiana |
|---|---|---|---|
| 🔴 Krytyczne | 5 | 5 | 0 (nowe ustalenia) |
| 🟡 Ważne | 33 | 25 | -8 |
| 🟢 Nice to Have | 29 | 21 | -8 |
| **Razem** | **67** | **51** | **-16** |

> **Uwaga**: Wszystkie 5 krytycznych z rewizji 1 zostało zaadresowane. 5 krytycznych w rewizji 2 to **nowe ustalenia** dotyczące: walidacji UUID, in-memory state, rozproszonej klasyfikacji symboli, niedostępności wykresu i braku testów jednostkowych frontendu.

## Rekomendowany plan działań

### Natychmiastowe (Krytyczne)
1. **Walidacja analysis_id** — dodać walidację formatu UUID4 do parametru ścieżki w GET `/analysis/{id}`, `/analysis/{id}/status` i WS `/ws/analysis/{id}`.
2. **Centralny rejestr instrumentów** — stworzyć jeden źródłowy rejestr w `app.core` z mapowaniami per-provider jako transformerami, eliminując rozproszenie w 5+ plikach.
3. **Accessible chart** — dodać `role="img"` z dynamicznym `aria-label` opisującym zakres dat i trend, lub ukrytą tabelę danych.
4. **Frontend unit testy** — skonfigurować Vitest + React Testing Library; dodać testy dla formatów, utility i kluczowych komponentów.
5. **In-memory state** — udokumentować ograniczenie jako known limitation dla MVP; zaplanować migrację do Redis/DB przed skalowaniem.

### Krótkoterminowe (Ważne)
1. **Rate limiting na pozostałych endpointach** — `/technical-analysis`, `/patterns`, `/fundamental-analysis`.
2. **ASGI lifespan handler** — `engine.dispose()`, zamknięcie httpx klientów, czyszczenie cache.
3. **Security headers** — `next.config.mjs` + weryfikacja nginx.
4. **React Error Boundary** — owinąć layout i/lub sekcje raportu.
5. **Ujednolicenie języka błędów** — fundamental.py: polskie → angielskie komunikaty.
6. **Usunięcie `from None`** — fundamental.py: przywrócić łańcuch wyjątków.
7. **Współdzielony FMP rate limiter** — jeden globalny licznik dla obu klientów FMP.
8. **E2E: asercje na zawartość raportu** — rozszerzyć testy o weryfikację danych.
9. **Wyekstrahować `useAnalysis` hook** — oddzielić logikę stanu od renderowania w `page.tsx`.
10. **Skonsolidować formatery i gauge** — wspólny `<GaugeBar>`, wspólny `formatValue`.

### Długoterminowe (Nice to Have)
1. Wyekstrahować `<Card>`, `<EmptyState>` jako reużywalne komponenty UI.
2. Usunąć martwy font loading z `layout.tsx`.
3. Wyczyścić nieużywane metody fmp_source.py, fmp_provider.py.
4. Obsłużyć unit `"m"` w period parsing.
5. Dodać `React.memo` do komponentów prezentacyjnych.
6. Runtime walidacja API responses (Zod).
7. Wyekstrahować helper `ohlcv_to_dataframe()` dla eliminacji duplikacji.

## OWASP Top 10 — Ocena bezpieczeństwa

| # | Kategoria OWASP | Status | Uwagi |
|---|---|---|---|
| A01 | Broken Access Control | ⚠️ Ryzyko | WebSocket `/ws/analysis/{id}` bez autentykacji (Backend Usp. #3). `analysis_id` brak walidacji UUID (Backend Usp. #1). Brak RBAC — wszystkie endpointy publiczne (akceptowalne dla MVP bez danych wrażliwych). |
| A02 | Cryptographic Failures | ✅ OK | Nie przechowuje danych wrażliwych użytkowników. API keys w zmiennych środowiskowych, nie w kodzie. Brak PII. |
| A03 | Injection | ✅ OK | SQLAlchemy ORM z parametryzowanymi zapytaniami — brak raw SQL. Walidacja symboli regex-em. Pydantic deserializacja request body. Brak `eval()`, `exec()`, template injection. |
| A04 | Insecure Design | ⚠️ Ryzyko | In-memory state (TTLCache) — restart = utrata danych (Backend Usp. #2). `raise ... from None` ukrywa przyczyny awarii (Backend Usp. #11). Brak Error Boundary na froncie (FE Usp. #7). |
| A05 | Security Misconfiguration | ✅ OK (poprawione) | CORS ograniczony (rewizja 1 fix). Rate limiting aktywny na kluczowych endpointach. Brak domyślnych credentials. Debug mode kontrolowany env var. **Uwaga**: brakuje nagłówków HTTP security w next.config (FE Usp. #5) — nginx może kompensować. |
| A06 | Vulnerable Components | ✅ OK | Zależności aktualne (FastAPI 0.115, Next.js 14.2, SQLAlchemy 2.x). Brak znanych CVE w bezpośrednich zależnościach. |
| A07 | Identification & Auth Failures | ℹ️ N/A | Brak systemu autentykacji — aplikacja analityczna bez kont użytkowników. WebSocket bez auth to ryzyko jeśli doda się multi-tenancy. |
| A08 | Software & Data Integrity | ✅ OK | Docker images budowane z oficjalnych base images. `pip install` z lockfile. Brak deserializacji untrusted data (Pydantic waliduje). |
| A09 | Security Logging & Monitoring | ⚠️ Częściowe | Logging skonfigurowany (`logging_config.py`). `logger.exception()` przy awariach. Brak structured logging (JSON), brak audit trail dla API calls, brak alertingu. |
| A10 | Server-Side Request Forgery | ✅ OK | Symbole walidowane regexem `[A-Za-z0-9/\-]{2,20}` — nie mogą zawierać URL. Endpointy nie przyjmują URL od użytkownika. Zewnętrzne API wywoływane z hardkodowanymi bazami URL. |

**Podsumowanie OWASP**: Brak krytycznych luk bezpieczeństwa z OWASP Top 10. Zidentyfikowane ryzyka (A01, A04, A09) są udokumentowane w ustaleniach raportu z konkretnymi rekomendacjami.

## Powiązane raporty

| Raport | Opis | Status |
|---|---|---|
| [sonar-report.md](sonar-report.md) | Analiza SonarQube for IDE — lokalna analiza kluczowych plików | ✅ Zaktualizowany |
