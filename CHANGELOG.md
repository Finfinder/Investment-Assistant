# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Discussions contact link in issue template config — directs users to Discussions before opening issues
- Support for 10 forex cross pairs (AUDCAD, AUDCHF, AUDJPY, CADJPY, CHFJPY, EURCHF, EURAUD, EURCAD, GBPCAD, GBPCHF) in all data providers and frontend suggestions
- Architecture test enforcing FOREX_PAIRS consistency across all data provider symbol maps

### Changed

- Replace discontinued/unavailable FRED CPI series: US (`CPIAUCSL` → `CPALTT01USM659N` YoY%), JP (`CPALTT01JPM659N` → `FPCPITOTLZGJPN` annual IMF), AU (`CPALTT01AUM659N` → `CPALTT01AUQ659N` quarterly OECD)
- Add `SERIES_YOY_UNITS` dict to convert EU HICP index to YoY% via FRED `units=pc1` parameter
- Add `SERIES_LOOKBACK_DAYS` dict for per-series lookback overrides (730 days for annual JP CPI)
- Rewrite index inflation scoring to use CPI YoY% deviation from 2% target instead of skipping CPI index values
- Rewrite commodity real-rate scoring to compute actual real rate (`fed_rate - cpi_yoy`) instead of heuristic
- Rename forex fundamental indicators from `_cpi` to `_inflation_yoy` and display inflation differential in percentage points

### Fixed

- Fix "Brak danych rynkowych" error for 10 forex cross pairs (AUDCAD etc.) — add missing symbol mappings to YFinance, TwelveData and FMP providers
- Fix null inflation data for JPY and AUD currency pairs caused by discontinued FRED OECD series
- Fix EU inflation always null — add FRED `units=pc1` parameter to convert Eurostat HICP index to YoY%
- Fix US CPI returning raw index value instead of YoY% — switch from `CPIAUCSL` (SA index) to `CPALTT01USM659N` (YoY%)
- Fix Docker healthchecks failing inside containers — replace `localhost` with `127.0.0.1` in `wget` commands
- Fix backend entrypoint `exec format error` on Linux — strip Windows CRLF line endings in Dockerfile
- Fix Next.js standalone server not accepting external connections — set `HOSTNAME=0.0.0.0` in frontend Dockerfile

### Added

- Docker entrypoint script (`entrypoint.sh`) that runs Alembic migrations before starting uvicorn
- `strategy_skip_reason` field on `AnalysisReport` — explains why no strategies were generated (e.g., neutral signals)
- DB fallback in `GET /analysis/{id}` — loads persisted report from database when TTL cache misses
- Frontend retry with linear backoff (3 attempts) when fetching completed analysis report
- Configurable indicator presets system (Investing.pl / TradingView) with frozen dataclass parameters and `IndicatorPreset` StrEnum
- 4 new technical indicators: ATR, Bull/Bear Power, StochRSI, ROC (13 total oscillator/momentum indicators)
- MACD crossover signal logic replacing histogram-based signal generation
- OHLCV cache in SQLite with delta-fetch strategy, staleness check for intraday timeframes, and graceful fallback
- Preset dropdown in analysis form (frontend) with accessibility support (label, keyboard nav, Tab order)
- `FetchFn` type alias for async fetch callbacks in cache service (proper `Callable` typing)

### Changed

- Extend default data period from 90 to 200 days for improved indicator accuracy
- Parameterize all 9 existing indicators via preset configuration instead of hardcoded values
- Indicator names now reflect active parameters (e.g., `CCI(14)` for Investing, `CCI(20)` for TradingView)

### Fixed

- Fix Pivot Points showing identical values for all S/R levels on intraday timeframes — use previous completed daily candle (D1) instead of last intraday candle for calculations, with graceful fallback when D1 fetch fails
- Fix race condition between COMPLETED status publication and report caching — pipeline now caches report before signaling completion via `complete()` method
- Fix missing `analysis_results` table in Docker — entrypoint runs `alembic upgrade head` before uvicorn startup
- Fix empty strategies showing generic message — display `strategy_skip_reason` explaining why no entry strategies were generated (neutral signals)
- Fix chart price precision for forex pairs (4 decimal places instead of 2), initial chart scaling to show relevant bars per timeframe, and zoom anchoring to keep right edge visible
- Fix empty candlestick chart on intraday timeframes (M15, H1, H4) — convert ISO timestamps to `UTCTimestamp` (Unix epoch seconds) instead of truncating to date strings, which caused duplicate keys silently rejected by lightweight-charts v5.1
- Fix flaky E2E axe-core accessibility test in CI — run Playwright against production build (`npm run build && npm start`) instead of dev server to eliminate incomplete HTML under concurrent load
- Fix flaky E2E axe-core accessibility test in CI — add `suppressHydrationWarning` to `<html>` and wait for full hydration before scanning

### Removed

- Remove `code-quality-report.md` and `sonar-report.md` from repository (generated reports should not be tracked)
- Remove deprecated `CURRENCYLAYER_API_KEY` and `MARKETSTACK_API_KEY` from `backend/.env.example` and `.env.production.example`

### Added

- `CONTRIBUTING.md` — contributor guidelines with prerequisites, coding conventions, testing strategy, and PR checklist
- `SECURITY.md` — security policy with responsible disclosure via GitHub Security Advisories
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.0
- `LICENSE` — MIT license
- `.github/PULL_REQUEST_TEMPLATE.md` — PR template with checklist aligned to CI pipeline
- `.github/ISSUE_TEMPLATE/bug-report.yml` — bug report form template
- `.github/ISSUE_TEMPLATE/feature-request.yml` — feature request form template
- `.github/ISSUE_TEMPLATE/config.yml` — issue template configuration
- E2E API mock infrastructure (`frontend/e2e/fixtures.ts`) with HTTP route interception and WebSocket mocking for Playwright tests
- Playwright test-results and playwright-report directories added to frontend `.gitignore`

- Automated accessibility testing with `@axe-core/playwright` (WCAG 2.1 AA audit)
- E2E accessibility test suite (`frontend/e2e/accessibility.spec.ts`): axe-core scans, keyboard navigation, report page structure
- Frontend lint (`frontend-lint`) and E2E (`frontend-e2e`) jobs in CI pipeline

- Rate limiting via `slowapi` on `/analysis` (10/min) and `/market-data` (30/min) endpoints
- Rate limiting on `/technical-analysis`, `/patterns`, and `/fundamental-analysis` endpoints (20/min each)
- `pip-audit` dependency scanning job in CI pipeline for detecting known vulnerabilities
- Auth middleware placeholder (`app/core/auth.py`) with no-op `require_auth` dependency for future JWT integration
- HTTPS/TLS server block template in nginx.conf (commented, ready for Let's Encrypt)
- `SensitiveFilter` formatter in logging — redacts sensitive data in DEBUG mode too
- Centralized `rate_limit.py` module with shared `Limiter` instance
- Centralized `validators.py` with canonical `SYMBOL_PATTERN` and `PERIOD_PATTERN` used by all API endpoints
- Shared `DailyRateLimiter` in `app.core.daily_rate_limiter` replacing duplicated rate-limit logic in providers
- Shared `_helpers.py` in `technical_analysis` module with `safe_last()` and `ohlcv_to_dataframe()` helpers
- Shared frontend utilities: `lib/format.ts` (confidence bar classes), `lib/signals.ts` (signal labels/colors)
- Concurrency control: `asyncio.Semaphore` limiting concurrent pipeline executions to 5
- Centralized `build_fallback_chain()` factory in `fallback_chain.py` used by both pipeline and market-data API
- Propagate `instrument_type` from backend pipeline through `AnalysisReport` to frontend chart component
- Code quality report (revision 2): `code-quality-report.md` with 51 findings
- SonarQube local analysis report: `sonar-report.md`

- Nginx reverse proxy with Docker Compose integration (port 80), health checks, and log volume
- Enhanced health endpoint returning application version and uptime (`GET /api/v1/health`)
- Dependency health endpoint checking database, yfinance, and API key status (`GET /api/v1/health/dependencies`)
- Structured logging configuration with configurable `LOG_LEVEL` setting
- Production environment example (`.env.production.example`)
- E2E test suite with Playwright (`frontend/e2e/analysis.spec.ts`)
- Architecture boundary tests (`backend/tests/architecture/test_import_boundaries.py`)
- Full pipeline integration test (`backend/tests/integration/test_full_pipeline.py`)
- Performance tests with k6 (`tests/performance/analysis.k6.js`)

- Data acquisition module with multi-provider fallback chain
  - yfinance provider (primary) with symbol/timeframe mapping and H4 resampling
  - Twelve Data provider (secondary) with async HTTP and rate limiting (800 req/day)
  - Financial Modeling Prep provider (tertiary) with economic calendar, COT reports, and treasury rates
  - Fallback chain manager with priority-based provider selection and timing logs
  - In-memory TTL cache for OHLCV data (intraday 300s, daily 3600s)
- Market data REST endpoint: `GET /api/v1/market-data/{symbol}`
- Technical analysis engine
  - 9 oscillator/momentum indicators with signal rating (RSI, Stochastic, CCI, ADX, AO, Momentum, MACD, Williams %R, Ultimate Oscillator)
  - Moving averages calculator: SMA and EMA for periods 5, 10, 20, 50, 100, 200
  - 5 pivot point types: Classic, Fibonacci, Camarilla, Woodie, DeMark
  - Signal summary aggregation with strong_buy/buy/neutral/sell/strong_sell thresholds
- Technical analysis REST endpoint: `POST /api/v1/technical-analysis`
- Pattern recognition module
  - Candlestick pattern detector: 15 patterns via TA-Lib (engulfing, hammer, doji, shooting star, morning/evening star, etc.) with bearish engulfing marked as "nóż"
  - Support/resistance level detector: local extrema via scipy, level clustering, touch-count strength scoring, EMA 50/200 bounce detection
  - Fibonacci retracement calculator: 5 levels (23.6–78.6%) with automatic swing high/low identification and active level marking
  - IKI (Impulse-Correction-Impulse) detector: impulse > 2×ATR, correction 38.2–61.8% Fibonacci, second impulse confirmation
  - Geometric chart pattern detector: ascending/descending/symmetric triangle, wedge, flag, pennant via trendline regression
- Pattern recognition REST endpoint: `POST /api/v1/patterns`
- Fundamental analysis module
  - FRED data source: 18 macro series (interest rates, CPI, employment) with 24h TTL cache
  - FMP economic data source: treasury rates, economic indicators, economic calendar with shared rate limiting
  - FMP COT reports: commitment of traders parsing with net positions and weekly changes
  - Forex fundamental analyzer: currency pair macro comparison (interest rate and inflation differentials), score -100..+100
  - Commodities fundamental analyzer: COT positioning, USD strength, rate environment scoring
  - Indices fundamental analyzer: regional macro analysis (US, EU, UK, JP, AU, CA) with rate/unemployment scoring
- Fundamental analysis REST endpoint: `POST /api/v1/fundamental-analysis` with auto-routing by instrument type
- Signal aggregation module
  - Signal aggregator: normalizes TA, pattern, and fundamental signals to -1.0..+1.0 scale
  - Weighted scoring system: configurable weights (TA 50%, patterns 30%, fundamental 20%) with direction thresholds
- Strategy generator module
  - Entry calculator: aggressive (market price) and conservative (S/R level, Fibonacci level) entry scenarios
  - SL/TP calculator: stop loss via nearest S/R with ATR buffer, TP1 (R:R ≥ 1:1), TP2 (R:R ≥ 1:2) with ATR fallbacks
  - Confidence scorer: 0-100% scoring from TA agreement, pattern confirmation, fundamental alignment, ADX trend strength
  - Report builder: composes full AnalysisReport with 2-3 strategy scenarios per direction
- Asynchronous analysis pipeline with 6-step orchestration, in-memory status tracking, and graceful degradation
- Analysis REST API: `POST /api/v1/analysis`, `GET /api/v1/analysis/{id}`, `GET /api/v1/analysis/{id}/status`
- Analysis WebSocket: `WS /api/v1/ws/analysis/{id}` for live progress updates
- README and CHANGELOG documentation
- Frontend application (Next.js 14, TypeScript, TailwindCSS)
  - Analysis form with symbol autocomplete and timeframe selector
  - Real-time WebSocket progress indicator with pipeline step tracking
  - Interactive candlestick chart (lightweight-charts v5) with EMA, pivot, Fibonacci overlays and pattern markers
  - Signal summary gauges (MA, Indicators, Overall) with buy/neutral/sell counts
  - Oscillator and Moving Average indicator tables with color-coded signal badges
  - Pivot points table (Classic, Fibonacci, Camarilla, Woodie, DeMark)
  - Pattern list with confidence bars, bullish/bearish badges, and chart marker integration
  - Fundamental analysis panel with score bar and macro indicators
  - Strategy table with entry, SL, TP1, TP2, direction, and confidence
  - Collapsible accordion sections with ARIA accessibility
  - Scroll-spy navigation bar with IntersectionObserver
  - Responsive layout: mobile (360px+), tablet, desktop
  - Docker multi-stage build (node:20-alpine, non-root user)
  - Docker Compose integration with backend service

### Changed

- Fix `--accent` CSS color from `#3b82f6` to `#2563eb` for WCAG 2.1 AA contrast ratio compliance (4.58:1 white-on-accent)
- Fix badge text color from `text-accent` to `text-blue-400` in `page.tsx` and `FundamentalPanel.tsx` for WCAG AA contrast on dark background
- Fix button hover state from `hover:bg-blue-600` to `hover:bg-blue-700` in `AnalysisForm.tsx`
- Fix E2E test locators from `getByText()` to `getByRole("heading", ...)` for strictness and resilience
- Show progress UI placeholder immediately when analysis starts (before `analysisId` is received)
- Prefix user-facing error messages with "Błąd:" for consistent error identification
- E2E analysis tests use mocked API (`mockedPage` fixture) instead of requiring live backend
- E2E accessibility tests use mocked API for report page structure and axe-core audit
- Invalid symbol test uses `INVALIDXYZ123` (fails mock regex validation) instead of `!!!!INVALID!!!!`

- Fix `--muted` CSS color from `#6b7280` to `#9ca3af` for WCAG 2.1 AA contrast ratio compliance (7.01:1 on card background)
- `SignalGauge`: add native `<meter>` element with `aria-label` for screen reader support
- `FundamentalPanel` ScoreBar: add native `<meter>` element with bipolar range (-100/+100) and `aria-label`
- `CandlestickChart`: wrap chart in `<figure>` with dynamic `aria-label` showing candle count and date range
- Apply ruff auto-formatting to `test_chart_patterns.py` and `test_fmp_source.py`
- Fix import sorting in `test_chart_patterns.py` (numpy before local imports)
- Remove redundant per-method `import httpx` in `test_fmp_source.py` (keep single top-level import)
- Replace unused unpacked variables with `_` in `test_pipeline.py` (RUF059)
- Break long patch path lines in `test_pipeline.py` to stay within 120-char limit (E501)
- Replace bare float equality assertions with `pytest.approx()` in `test_fmp_source.py` and `test_pipeline.py`

- CORS restricted from `allow_methods=["*"]` / `allow_headers=["*"]` to explicit `["GET", "POST", "OPTIONS"]` / `["Content-Type"]`
- CSP header: removed `'unsafe-eval'` from `script-src` directive in nginx.conf
- HTTP→HTTPS redirect comment added to nginx.conf (enable after TLS provisioning)
- Input validation added to `/fundamental-analysis` endpoint via `validate_symbol()`
- DEBUG mode logging now filters sensitive data through `SensitiveFilter` (previously unfiltered)
- `FredSource.fetch_series()` now uses `asyncio.to_thread()` instead of blocking the event loop
- `analyze_forex()` and `analyze_index()` converted to async functions for consistency with `analyze_commodity()`
- `market_data.py` globals replaced with `@lru_cache` pattern for caches and fallback chain
- Symbol validation unified across all endpoints using shared `validate_symbol()` from `validators.py`
- Period validation added to `/technical-analysis` and `/patterns` endpoints via `validate_period()`
- Regex patterns in `entry_calculator.py` and `sl_tp_calculator.py` pre-compiled at module level
- `AnalysisForm` component upgraded with full ARIA combobox: `role="combobox"`, `role="listbox"`, `role="option"`, keyboard navigation (ArrowUp/Down, Enter, Escape), `aria-activedescendant`
- Frontend tables and progress indicator enhanced with `aria-live` regions, `<caption>` elements, and `type="button"` attributes
- Frontend Dockerfile fixed: conditional `COPY` for `public/` directory
- Tailwind config: removed dead `./src/pages/**` glob path
- Duplicate `confidenceBarClass` consolidated into `lib/format.ts`
- Duplicate signal label/color maps consolidated into `lib/signals.ts`

- Docker Compose: backend and frontend use `expose` instead of `ports`, traffic routed through nginx
- Frontend WebSocket URL resolution supports relative paths for nginx proxy
- README updated with architecture diagram, Docker setup instructions, configuration reference, and testing commands
- Extract shared instrument classifier to `app.core.instrument_classifier` removing duplication from `fundamental.py` and `pipeline.py`
- Move signal aggregation from `report_builder` to `pipeline.py` step 5, fixing domain module independence contract
- Replace unbounded `analysis_tasks` dict with `TTLCache(maxsize=1000, ttl=3600)` in pipeline and analysis API to prevent memory leak
- Add full type annotations to pipeline helper methods (`_step_fetch_data`, `_step_technical_analysis`, `_step_pattern_recognition`)
- Replace soft assertions (`if results:`) with hard assertions in chart pattern tests
- Reorganize test files: move 6 unit tests from `tests/` root to `tests/unit/`, move `test_database.py` to `tests/integration/`

### Fixed

- Unreachable timeframe validation in `analysis.py` removed (Pydantic handles at deserialization)
- Removed unused `CURRENCYLAYER_API_KEY` and `MARKETSTACK_API_KEY` from Settings
- Removed unused `DataCache` protocol from `cache.py`
- Removed unused logging import from `interfaces.py`
- Removed unused `slowapi` and `websockets` from active dead-code (slowapi now active)
- WebSocket `onmessage` now logs parse errors instead of silently swallowing them

- Resolve 36 mypy strict-mode errors: list variance, nullable arithmetic, NDArray types, unused type:ignore suppressions
- Fix chart pattern test data generators to produce oscillating data for `argrelextrema` peak/trough detection
- Fix `fred_source.py` returning untyped cached value (`Any`) instead of `float`

## [0.1.0] - 2025-03-26

### Added

- Project foundation: FastAPI app, Pydantic settings, async SQLAlchemy with SQLite
- Domain models: 7 enums and 11 Pydantic models for OHLCV, indicators, signals
- Database layer with Alembic migrations
- Docker and Docker Compose setup
- CI pipeline with pytest, ruff, and mypy
- Health check endpoint: `GET /api/v1/health`
