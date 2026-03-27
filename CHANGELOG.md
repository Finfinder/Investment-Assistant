# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Apply ruff auto-formatting to `test_chart_patterns.py` and `test_fmp_source.py`
- Fix import sorting in `test_chart_patterns.py` (numpy before local imports)
- Remove redundant per-method `import httpx` in `test_fmp_source.py` (keep single top-level import)
- Replace unused unpacked variables with `_` in `test_pipeline.py` (RUF059)
- Break long patch path lines in `test_pipeline.py` to stay within 120-char limit (E501)
- Replace bare float equality assertions with `pytest.approx()` in `test_fmp_source.py` and `test_pipeline.py`

### Added

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
- Code quality report (revision 2): `code-quality-report.md` with 51 findings
- SonarQube local analysis report: `sonar-report.md`

### Changed

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

### Fixed

- Unreachable timeframe validation in `analysis.py` removed (Pydantic handles at deserialization)
- Removed unused `CURRENCYLAYER_API_KEY` and `MARKETSTACK_API_KEY` from Settings
- Removed unused `DataCache` protocol from `cache.py`
- Removed unused logging import from `interfaces.py`
- Removed unused `slowapi` and `websockets` from active dead-code (slowapi now active)
- WebSocket `onmessage` now logs parse errors instead of silently swallowing them

### Added

- Nginx reverse proxy with Docker Compose integration (port 80), health checks, and log volume
- Enhanced health endpoint returning application version and uptime (`GET /api/v1/health`)
- Dependency health endpoint checking database, yfinance, and API key status (`GET /api/v1/health/dependencies`)
- Structured logging configuration with configurable `LOG_LEVEL` setting
- Production environment example (`.env.production.example`)
- E2E test suite with Playwright (`frontend/e2e/analysis.spec.ts`)
- Architecture boundary tests (`backend/tests/architecture/test_import_boundaries.py`)
- Full pipeline integration test (`backend/tests/integration/test_full_pipeline.py`)
- Performance tests with k6 (`tests/performance/analysis.k6.js`)

### Changed

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

- Resolve 36 mypy strict-mode errors: list variance, nullable arithmetic, NDArray types, unused type:ignore suppressions
- Fix chart pattern test data generators to produce oscillating data for `argrelextrema` peak/trough detection
- Fix `fred_source.py` returning untyped cached value (`Any`) instead of `float`

### Added

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

## [0.1.0] - 2025-03-26

### Added

- Project foundation: FastAPI app, Pydantic settings, async SQLAlchemy with SQLite
- Domain models: 7 enums and 11 Pydantic models for OHLCV, indicators, signals
- Database layer with Alembic migrations
- Docker and Docker Compose setup
- CI pipeline with pytest, ruff, and mypy
- Health check endpoint: `GET /api/v1/health`
