# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-07-08

### Changed

- Cache Docker layers for the frontend builder stage: switch release image builds to `docker buildx build` with GitHub Actions cache (`type=gha`) and add an npm cache mount in `frontend/Dockerfile`, reducing CI build times ([#96](https://github.com/Finfinder/Investment-Assistant/issues/96))
- Centralize error handling: add correlation-ID middleware and sanitized `{"error", "reference"}` JSON responses for all errors; preserve the full exception chain in server logs and stop masking it with `from None` ([#113](https://github.com/Finfinder/Investment-Assistant/issues/113))

### Security

- Ensure API error responses never leak stack traces, internal paths, or exception details; clients receive only a generic message and a correlation reference UUID ([#113](https://github.com/Finfinder/Investment-Assistant/issues/113))
- Re-review of [#113](https://github.com/Finfinder/Investment-Assistant/issues/113): confirm unhandled errors always return a generic message (no `type(exc).__name__` leak even in DEBUG), and audit all `HTTPException` `detail` values across `app/` — none expose sensitive/internal data, so no code change required for the HTTP-exception handler

### Fixed

- Fix `riskRewardClass` returning a "safe" green class for negative risk/reward ratios: negative R/R now maps to `text-red-400`, and the `0.5` threshold is extracted to a named constant ([#126](https://github.com/Finfinder/Investment-Assistant/issues/126))
- Fix WebSocket per-IP limiter memory leak and DoS vulnerability: add Redis-backed connection limiter with atomic Lua scripts, TTL-based expiration (300s), in-memory fallback, max 5 concurrent connections per IP, and warning on limit exceeded ([#115](https://github.com/Finfinder/Investment-Assistant/issues/115))

## [0.4.0] - 2026-07-08

### Changed

- Reorganize `CHANGELOG.md`: merge duplicate subsection headers (Security, Tests, Fixed, Changed, Added) in `[Unreleased]` and `[0.1.0]`, remove internal code-review round sections, and move the floating candlestick-pattern entry under `### Added`

### Security

- Add security response headers (HSTS, CSP `default-src 'none'`, X-Frame-Options `DENY`, X-Content-Type-Options `nosniff`, Referrer-Policy) via `SecurityHeadersMiddleware` in production mode; configure nginx to add HSTS on HTTPS and scope CSP to the frontend location ([#114](https://github.com/Finfinder/Investment-Assistant/issues/114))
- Rate limiting: defend against `X-Forwarded-For` spoofing by validating the header against configured `TRUSTED_PROXIES`, preferring the verified JWT subject as the rate-limit key, and falling back to the direct peer when no trusted proxy is configured ([#112](https://github.com/Finfinder/Investment-Assistant/issues/112))
- Rate limiting: remove the flawed `X-Forwarded-For` spoofing heuristic that compared chain length to the number of configured CIDR rules (`len(hops) > len(TRUSTED_PROXIES) + 1`); chain length is no longer treated as a spoofing signal, avoiding false positives on legitimate multi-proxy topologies behind a single broad CIDR ([#156](https://github.com/Finfinder/Investment-Assistant/pull/156))

### Tests

- Refactor formatting helper tests (`confidenceBarClass`, `formatRiskReward`, `formatValue`) to use `it.each` for improved readability and maintainability
- Add comprehensive unit tests for PatternDetailModal component covering open/close behavior, escape key handling, and all field rendering ([#100](https://github.com/Finfinder/Investment-Assistant/issues/100))
- Add error path coverage for fundamental data providers (BFS, BLS, OECD SDMX, StatCan CPI sources) with comprehensive unit tests covering edge cases and exception handling ([#121](https://github.com/Finfinder/Investment-Assistant/issues/121))

### Fixed

- nginx: remove deprecated `X-XSS-Protection` header and fix `add_header` inheritance — the frontend `location /` block defines its own `add_header` directives, which stopped inheriting server-level headers; the deprecated header is now omitted entirely rather than silently dropped on frontend responses ([#114](https://github.com/Finfinder/Investment-Assistant/issues/114))
- Pattern detector exceptions crashing `/api/v1/patterns` endpoint — added per-detector try/except isolation with graceful degradation and `warnings` field in response ([#116](https://github.com/Finfinder/Investment-Assistant/issues/116))
- Translate inline comments to English in `patterns.py` for consistency with backend codebase
- Strengthen `test_detector_failure_isolation` to verify working detectors actually contribute results via sentinel pattern

- CI: Add missing `type: string` to `automation-sha` input in `reusable-open-next-version-branch.yml` to fix invalid workflow file error
- Security: Pin automation repository checkout to commit SHA and add allowlist validation in `reusable-open-next-version-branch.yml` to fix CodeQL `actions/untrusted-checkout/high` alert ([#135](https://github.com/Finfinder/Investment-Assistant/issues/135))
- Security: Redact clear-text API key names in `main.py` startup logs - replaced with count-based logging to fix CodeQL `py/clear-text-logging-sensitive-data` alert ([#134](https://github.com/Finfinder/Investment-Assistant/issues/134))
- Security: Extended `JSONFormatter` to sanitize `record.args` and exception tracebacks to prevent sensitive data leakage via log arguments and stack traces
- Security: Extended `_SENSITIVE_KEYS` with API key names (`twelve_data_api_key`, `fmp_api_key`, `fred_api_key`) and infrastructure secrets (`redis_password`, `database_url`)

### Changed

- Frontend: reformat `tsconfig.json` to multi-line array style and add `"target": "ES2017"`
- CI: limit `push` trigger to `main` and `release/**` branches to avoid duplicate CI runs on task branches with open PRs

- CI: Restore `actions/checkout` SHA pin in `reusable-version-consistency.yml` to prevent tag hijacking; update contract test assertion to match SHA format
- CI: Remove `sonarcloud` from `release` job `needs` to unblock release pipeline; SonarCloud still runs in parallel
- CI: Add `.vscode/settings.json` to `.gitignore` to prevent committing local SonarLint configuration

### Added

- SonarCloud project integration: `sonar-project.properties` configuration, `sonarcloud` job in CI and release workflows, SonarCloud badge in README.md ([#2](https://github.com/Finfinder/Investment-Assistant/issues/2))
- Redis caching for market data and analysis results: `RedisCache` class with JSON serialization and `InMemoryCache` fallback, `RedisManager` singleton for connection lifecycle, Redis service in docker-compose.yml, `REDIS_URL` and `REDIS_MAX_CONNECTIONS` configuration in Settings

- Fix `test_settings_cors_origins_default` to match actual `CORS_ORIGINS` default including `http://localhost`
- Security: `_mask_url()` in `redis.py` now masks password-only URLs (`redis://password@host`) to prevent credential leakage in logs
- Security: Removed `or ["http://localhost:3000"]` fallback in WebSocket CORS check to enforce explicit origin allowlist (fail-closed)
- Security: Patch PostCSS XSS vulnerability (postcss < 8.5.10) by adding npm overrides in frontend/package.json to force postcss >= 8.5.10 across the dependency tree, including the transitive dependency from Next.js 15.5.18 ([#133](https://github.com/Finfinder/Investment-Assistant/issues/133))
- Types: Fixed mypy errors — added `_client` type annotation in `RedisManager`, `AsyncIterator[None]` return type for `lifespan`, replaced `Optional[X]` with `X | None`

- Added `test_mask_url.py` with 12 unit tests covering all Redis URL formats for password masking

- Security: Redis healthcheck now uses `REDISCLI_AUTH` env var instead of `-a` flag to avoid password exposure in process args; fails fast if `REDIS_PASSWORD` is empty
- Security: WebSocket per-IP rate limiter now uses UUID4 connection IDs instead of `time.monotonic()` timestamps to prevent theoretical collision edge case
- Resilience: Cache validation errors in analysis and market data endpoints now treated as cache miss with invalidation instead of returning 500
- Unit tests for API validators: `test_validators.py` covering symbol, period, and UUID4 validation (21 test cases)

- Documentation: Architecture diagram in README.md updated to include Redis caching layer, reflecting actual docker-compose.yml topology (Backend ↔ Redis) ([#104](https://github.com/Finfinder/Investment-Assistant/issues/104))
- Security: Removed hardcoded Redis password fallback in docker-compose.yml and `.env.example` - now requires explicit `REDIS_PASSWORD` environment variable
- Security: Added WebSocket origin check in `analysis_websocket` to reject connections from unauthorized origins
- Security: Added per-IP rate limiting for WebSocket connections (max 5 concurrent per IP in 60s window)
- Race condition: Added `asyncio.Lock` for atomic guard against duplicate `analysis_id` in `trigger_analysis` endpoint
- Error handling: Added exception logging in `_run_pipeline` with `logger.exception()` for failed pipeline executions
- Stability: Changed `_background_tasks` from `TTLCache(maxsize=1000)` to plain `dict` — active tasks are no longer at risk of eviction by size limit
- **ISSUE-1**: Pipeline exceptions now call `pipeline._fail()` to update `analysis_tasks` status to FAILED
- **C-1**: Added Redis password validation in `lifespan()` - raises `RuntimeError` if `REDIS_PASSWORD` is empty in production
- **H-1/H-2**: Added cleanup of `_ws_connections_per_ip` entries on WebSocket disconnect and empty list removal
- **BUG-3**: Made `RedisManager.reset()` async and now closes connection before resetting
- **BUG-4**: Added `PackageNotFoundError` fallback for `_APP_VERSION` in health endpoint (returns "dev" if package not installed)
- **GAP-3**: Added unit test for `create_redis_cache()` factory

- Unit tests for frontend components using React Testing Library and Vitest: Section, FundamentalPanel, IndicatorTable (MovingAverageTable, OscillatorTable), PatternList, AnalysisForm, ChartToolbar, PivotTable, StrategyTable, SignalGauge, ProgressIndicator (112 test cases total)
- Test setup file `__tests__/setup.ts` with jsdom environment configuration, browser API mocks (IntersectionObserver, ResizeObserver, WebSocket, localStorage)

- CI workflow cache steps: restored missing `npm ci` in `frontend-lint`, `frontend-test`, and `frontend-e2e` jobs; fixed cache paths from `.next/cache` to `frontend/.next/cache` since `defaults.run.working-directory` does not apply to `uses:` steps; removed unsupported `working-directory` key from `actions/cache/restore@v4` and `actions/cache/save@v4` steps in release workflow

- Cache npm dependencies and Next.js build artifacts in GitHub Actions CI and release workflows — `actions/cache@v4` with `hashFiles('frontend/package.json', 'frontend/next.config.mjs', 'frontend/tsconfig.json')` key for build cache; `setup-node@v5` with `cache: "npm"` for dependency cache; reduces frontend CI job times by 30-50% on cache hit

- Synchronized `.github/gh-sync.json` with GitHub repository labels: added 6 missing labels (`duplicate`, `good first issue`, `help wanted`, `invalid`, `question`, `wontfix`) and 4 Dependabot labels (`dependabot`, `python`, `javascript`, `ci`); local label set now matches GitHub (20 labels total)

- Unit tests for frontend formatting helpers: `formatValue`, `confidenceBarClass`, `formatRiskReward`, `riskRewardClass` — 36 test cases covering null/undefined handling, boundary values, edge cases (NaN, Infinity, -0, negative numbers)

- `calibrate_signal_thresholds.py` now supports real OHLCV data calibration via `--real` CLI flag and optional `--step-size` parameter; adds `run_with_real_data()` async orchestrator building calibration samples from live OHLCV data through the full pattern-recognition, technical-analysis, and SL/TP pipeline; `REAL_DATA_PERIOD` configures per-timeframe historical data ranges (`M15: 55d`, `H1/H4: 700d`, `D1: 5y`, `W1: 10y`)

- Threshold calibration infrastructure for `BULLISH_THRESHOLD` / `BEARISH_THRESHOLD` in `signal_aggregation`: added optional `bullish_threshold` and `bearish_threshold` parameters to `determine_direction()` (defaults preserve existing behavior), new `threshold_calibration.py` module with `CalibrationSample`, `CandidateMetrics`, `label_signal_outcome()`, `evaluate_candidates()`, and `recommend_candidate()` pure functions, and `backend/scripts/calibrate_signal_thresholds.py` CLI runner generating a JSON calibration report; threshold constants in `scoring.py` remain at `BULLISH_THRESHOLD = 0.15` / `BEARISH_THRESHOLD = -0.15` — no live data was available during this iteration to justify a change

- `W20` now maps to the `PL` region in index fundamental analysis; first iteration uses FRED/OECD Polish macro series (`IR3TIB01PLM156N`, `CPALTT01PLM659N`, `LRHUTTTTPLM156S`, `CLVMNACSCAB1GQPL`) with a planned future GUS BDL fallback for fresher country CPI data

- `PatternList` reliability filter: checkbox "Pokaż tylko ★★+" filtering out patterns with reliability below 2; category tabs and expand/collapse state reset on filter toggle; context-aware empty state message distinguishing filter-caused vs category-caused empty results
- E2E test suite `e2e/pattern-list-filter.spec.ts` (7 tests) covering checkbox default state, filtering, full-list restore, category counters, accessibility (ARIA label), state reset on toggle, and empty-state message with a self-contained `route.fulfill` mock
- `Doji` pattern (reliability: 1, candlestick) added to `e2e/fixtures.ts` mock data to support reliability filter test scenarios

- `.github/workflows/third-party-action-pinning.yml` and `.github/workflows/reusable-third-party-action-pinning.yml` — repo-local mirror of the monorepo SHA-pinning guard enforcing full 40-character SHA for third-party actions (stage 1)
- Staleness-aware CPI fallback layer for `cpi_us`, `cpi_ca`, `cpi_ch`: new `CpiFallbackSource` with per-country sources (`BlsCpiSource`, `StatCanCpiSource`, `BfsCpiSource`), shared `MacroObservation` model, and `cpi_yoy` helper utilities (period parsing, YoY computation, freshness checks)
- New unit test coverage for CPI fallback stack: `test_cpi_yoy.py`, `test_cpi_fallback_source.py`, `test_bls_cpi_source.py`, `test_statcan_cpi_source.py`, `test_bfs_cpi_source.py`, plus routing/regression updates in FRED/Macro/forex/indices/commodities tests

- Export `toChartTime()` from `CandlestickChart.tsx` and add Vitest unit tests covering UTC conversion, intraday timestamp differentiation, timezone normalization, and `buildPatternMarkers` regression scenarios
- OECD SDMX integration for monthly Japan CPI YoY (`cpi_jp`) in backend fundamental analysis via dedicated `OecdSdmxSource` and `MacroDataSource` routing layer
- `frontend-test` job in CI workflow running `npm run test` (Vitest) for unit test coverage on push/PR
- `npm run test` step added to release workflow before E2E tests, ensuring unit tests validate before publishing

- `threshold_calibration.evaluate_candidates()` now uses inlined `_classify_direction()` instead of lazy-importing `determine_direction()` from `scoring` module, eliminating a runtime cross-module dependency while preserving identical threshold comparison behavior

- `CalibrationRunner.run_simple_stub()` now emits a `WARNING` log when the generated sample count is below `CONFIG["min_samples"]` ensuring the operator is informed when a report is produced from statistically insufficient data; the report is still returned to preserve existing behavior
- `backend/scripts/calibrate_signal_thresholds.py` report payload now includes configurable calibration metadata (`configuration.config_version`, `configuration.symbols`, `configuration.timeframes`, `configuration.period`) plus recommendation metadata (`action`, `symmetry`); the CLI now supports `--symbol-list`, repeated `--timeframe`, period overrides, and window-size overrides, and the calibration summary prints valid `0.0` percentage values instead of hiding them
- calibration internals were refactored to smaller helper functions to reduce function complexity (`run_simple_stub`, `evaluate_candidates`) while preserving behavior
- `SignalAggregator.normalize_pattern_signal()` now uses `relevance_score` as the primary signal strength for each pattern (with fallback to `confidence` when `relevance_score == 0.0`); patterns with higher contextual relevance (recency, proximity, confidence) carry proportionally more weight in the pattern component of the final signal; `RELIABILITY_MULTIPLIER` continues to act as an independent quality amplifier
- `ConfidenceScorer.calculate_confidence()` now uses `relevance_score` as the primary pattern strength in the pattern confirmation component (25% weight), with fallback to `confidence` when `relevance_score == 0.0`; confirming patterns contribute positively and opposing patterns subtract proportionally to their strength and reliability, providing a more nuanced confidence score that reflects pattern contextual relevance alongside reliability ratings
- `PatternList` reliability filter checkbox "Pokaż tylko ★★+" is now checked by default, so only patterns with reliability ≥ ★★ are shown on initial render; updated 6 E2E tests in `pattern-list-filter.spec.ts` to reflect the new default state
- Refactored candlestick pattern recognition internals to remove SonarQube duplicated-literal and cognitive-complexity issues while preserving the public detection contract; cleaned the Playwright `mockedPage` fixture parameter name to avoid a React Hooks false positive.
- `FR40` now uses the `EU` index fundamental-analysis region (`ecb_rate` / `cpi_eu`) and appears in frontend `POPULAR_INSTRUMENTS` autocomplete suggestions, with backend and frontend regression tests.
- Removed unsupported `USOIL` from frontend `POPULAR_INSTRUMENTS` suggestion list; backend does not classify or map this symbol via any provider. Added regression test `popularInstruments.test.ts` to guard against unsupported symbols appearing in the suggestion list.
- `FredSource.fetch_series()` now uses a short-lived negative cache (5 minutes) for `None` outcomes (empty series and handled fetch errors), reducing repeated calls to unavailable FRED series while preserving recovery after TTL expiry
- `FredSource` now supports observation-level fetch (`fetch_series_observation()` / `fetch_indicator_observation()`) with period metadata, while preserving public `fetch_series()` and `fetch_indicator()` contracts
- `FredSource` now resolves effective lookback dynamically from FRED `frequency_short` metadata (`get_series_info`) with cache/negative-cache, while keeping `SERIES_LOOKBACK_DAYS` as emergency overrides for stale or irregular series
- `MacroDataSource` now routes `cpi_us`, `cpi_ca`, and `cpi_ch` through the dedicated CPI fallback orchestration while keeping `cpi_jp` on OECD SDMX and all remaining indicators on FRED
- GitHub Actions bumped to Node.js 24 runtime: `actions/checkout` v4→v5, `actions/setup-python` v5→v6, `actions/setup-node` v4→v5, `actions/upload-artifact` v5→v6, `actions/download-artifact` v6→v7 across `ci.yml`, `release.yml`, `reusable-next-version-request.yml`, `reusable-open-next-version-branch.yml`, and `reusable-third-party-action-pinning.yml`
- `.github/workflows/reusable-version-consistency.yml`, `reusable-next-version-request.yml`, `reusable-open-next-version-branch.yml` — synced to canonical mirror via centralized sync engine; replaced locally vendored scripts (`repository/.github/scripts/`) with cross-repo AI_Instruction checkout invoking `ai_instruction/scripts/`; sensitive env vars now set via `$env:*` instead of inline `${{ inputs.* }}` expressions
- `.github/workflows/reusable-third-party-action-pinning.yml` — synced to repo-local policy bundle; policy resolved from `.github/actions-security/zizmor.yml` instead of cross-repo checkout
- `.github/actions-security/zizmor.yml` and `.gitignore` — added repo-local zizmor policy bundle and unblocked `.github/actions-security/` from gitignore so the policy file is tracked
- `backend/tests/unit/test_release_workflow_contract.py` — extended with `test_third_party_action_pinning_uses_repo_local_policy_bundle` asserting the local policy bundle contract

- Added a 540-day lookback override for quarterly FRED `GDP` so US index fundamental analysis keeps the informational `gdp` indicator available during delayed or temporarily stalled GDP updates
- Replaced the browser-native symbol `datalist` popup in `AnalysisForm.tsx` with a dark-theme suggestions panel consistent with form controls (`card`/`border`/`accent` tokens), preserving uppercase filtering from `POPULAR_INSTRUMENTS`; added E2E accessibility regressions for styled suggestions visibility, keyboard selection (`Enter`), and close behavior (`Escape`)
- Added annual World Bank/IMF fallback series for AUD CPI (`CPALTT01AUQ659N` -> `FPCPITOTLZGAUS`) so `cpi_au` can still populate fundamental analysis when quarterly OECD/FRED data is unavailable
- `.github/workflows/reusable-version-consistency.yml` — restored the repo-local `validate-version-consistency.ps1` path for release/CI validation so the workflow no longer depends on a stale cross-repo checkout of `AI_Instruction` that can fail with `Join-Path` missing `ChildPath`; added a workflow contract test covering the local validator path

- Corrected the `commit-created` workflow output in `reusable-open-next-version-branch.yml` so the push step no longer skips when the automation creates the next-version branch commit
- Removed the duplicate `## [0.1.0]` heading so changelog-based release notes always resolve to a single version section
- Restored valid TOML/JSON in `backend/pyproject.toml` and `frontend/package.json` after `open-next-version-branch` script corrupted them via ambiguous `$1` regex backreference (root cause fixed in `AI_Instruction/scripts/version-target-strategies.ps1`)
- Extracted duplicated `"Analysis not found"` string literal in `backend/app/api/v1/analysis.py` into a module-level constant `_ANALYSIS_NOT_FOUND`
- Replaced nested ternary operator for `baseColor` in `buildPatternMarkers()` with an `if/else if/else` block to resolve SonarQube S3358
- Replaced custom `<ul role="listbox">` combobox pattern in `AnalysisForm.tsx` with native `<datalist>` to resolve SonarQube S6819; wrapped spinner text in `<span>` to resolve S6772; removed now-dead `inputRef`/`useRef` and simplified state (removed `showSuggestions`, `activeIndex`); updated `accessibility.spec.ts` to replace broken listbox-based keyboard navigation tests with a datalist-aware integration test — code review performed
- Resolved SonarQube S3358 in `backend/app/modules/fundamental_analysis/indices.py` and `commodities.py` — replaced nested conditional expressions with `if/elif/else` blocks
- Resolved SonarQube S3776 in `backend/app/modules/fundamental_analysis/forex.py` — extracted summary-building logic into `_build_forex_summary()` to reduce `analyze_forex` Cognitive Complexity below the allowed threshold
- Applied `pytest.approx()` to float equality assertions in `backend/tests/unit/test_fred_source.py` to resolve SonarQube S1244
- Applied `pytest.approx()` to float equality assertions in `backend/tests/unit/test_forex_analyzer.py` and `backend/tests/unit/test_indices_analyzer.py` to resolve SonarQube S1244
- Extracted magic numbers in `backend/app/modules/fundamental_analysis/forex.py` and `indices.py` into named module-level constants (`_RATE_DIFF_WEIGHT`, `_INFLATION_DIFF_WEIGHT`, `_SCORE_CLAMP`, `_DIRECTION_THRESHOLD`, etc.) to improve calibration maintainability
- Resolved SonarQube S3776 in `backend/app/modules/fundamental_analysis/data_sources/bfs_cpi_source.py` — extracted `parse_point` inner function in `_extract_latest_from_points` to reduce Cognitive Complexity below the allowed threshold
- Corrected `test_post_forex_analysis` patch target in `backend/tests/unit/test_fundamental_api.py` from `forex.FredSource` to `forex.MacroDataSource` (phase 6 refactored `forex.py` to use `MacroDataSource`; stale patch target caused `AttributeError` and a failing test)
- Added `FR40` to `INDEX_SYMBOLS` in `backend/app/core/instrument_classifier.py` — `classify_instrument("FR40")` now returns `InstrumentType.INDEX`, resolving the inconsistency with YFinance `SYMBOL_MAP` which already mapped `FR40 → ^FCHI`; added `test_fr40_is_index` regression test — code review performed
- Replaced `logger.error()` with `logger.exception()` in `patterns.py` `detect_patterns()` except block to preserve the full exception traceback in error logs (SonarQube S8572)
- Applied `pytest.approx()` to float equality assertions in `backend/tests/unit/test_aggregator.py` and `backend/tests/unit/test_scoring.py` to resolve SonarQube S1244

- Normalized `python` label color to lowercase hex (`3572a5`); assigned unique colors to `dependabot` (`006b75`) and `ci` (`bfdadc`) to avoid visual ambiguity with `frontend`/`backend`
- Added `repo.slug` format validation and `roadmapIssue.bodyPath` path traversal guard in `scripts/sync-github-meta.ps1`

## [0.1.0] - 2026-05-08

### Fixed

- Updated the backend release workflow contract test to validate the repo-local reusable workflow adapters instead of the retired cross-repository `@main` references
- Added the missing `session_factory` type annotation in `MultiTimeframeFetcher` so release mypy validation for `backend/app/modules/data_acquisition/multi_timeframe.py` passes again
- Replaced cross-repository `uses: Finfinder/AI_Instruction/.github/workflows/reusable-*.yml@main` calls in `ci.yml`, `release.yml` and `open-next-version-branch.yml` with local wrapper copies, and vendored the version-consistency validator into the repo to remove the failing runtime dependency on `AI_Instruction`

### Added

- Full release publishing for tagged versions: GitHub Release notes from `CHANGELOG.md` plus GHCR images for `backend`, `frontend`, and repo-local `nginx`

### Changed

- Analysis now runs as a native multi-timeframe pipeline: daily data powers pivot points, an internal weekly context powers long-term trend, and pattern scanning consolidates results from D1/H1/M15 into the report and the "Ramy czasowe" UI while preserving the single public request timeframe and main-timeframe chart markers

- `docker-compose.yml` now builds the local `nginx` service from `nginx/Dockerfile` so local deployments and released reverse-proxy images use the same source
- `.github/workflows/release.yml`: inline validation of `next_version` manifest replaced by shared reusable workflow `Finfinder/AI_Instruction/.github/workflows/reusable-next-version-request.yml`; added `backend/tests/unit/test_release_workflow_contract.py` asserting the shared adapter is used and no inline validator remains.

### Security

- Upgraded `pytest` from `8.x` to `>=9.0.3,<10.0.0` and `pytest-asyncio` from `0.x` to `>=1.3.0,<2.0.0` in `backend/pyproject.toml` to remediate CVE-2025-71176 (CWE-379: insecure temp directory creation; CVSS 6.8 MEDIUM)

- `.github/workflows/open-next-version-branch.yml`: automated next-version branch creation triggered by successful Release workflow; updates `backend/pyproject.toml`, `frontend/package.json` and `README.md` with the `next_version` provided before the release
- `.github/workflows/release.yml`: new Release workflow adapter uploading `next-version-request` artifact for the central automation workflow in `AI_Instruction`
- Chart layer visibility toolbar — 4 chip-style toggle buttons (EMA, Pivot Points, Fibonacci, Formacje) above the candlestick chart; preferences persisted in `localStorage`
- `ChartLayerVisibility` interface and `DEFAULT_LAYER_VISIBILITY` constant in `src/types/index.ts`
- `ChartToolbar` component with `aria-pressed` accessibility attribute for each toggle
- Unit tests for `buildPatternMarkers` grouping logic (6 cases) with Vitest; `vitest.config.ts` added
- 2 new E2E tests for `ChartToolbar` (toolbar default states, toggle interaction)

- Classic Pivot Points visual hierarchy: PP rendered with `lineWidth: 2`, R2/R3/S2/S3 with `axisLabelVisible: false` — reduces axis label clutter from 7 to 3 pivot labels
- `buildPatternMarkers()` now groups patterns detected on the same candle into a single marker with combined name (e.g. "Hammer / Doji"); color: all bullish → green, all bearish → red, mixed → gray

- `.gitignore`: add `!.github/release/` exception so `next-version.json` is not blocked by the blanket `.github/*` rule during release validation
- Target price "Cel" line disappearing after chart layer toggle — added `layerVisibility` to `useEffect` dependencies
- `createPriceLine` `lineWidth` type error (`as const` on expression) causing Next.js build failure
- E2E toolbar locators scoped to chart `aria-label` to avoid strict mode violation with duplicate button names

- 13 new candlestick patterns via TA-Lib (total: 28) — Abandoned Baby, Dark Cloud Cover, Dragonfly/Gravestone Doji, Evening/Morning Doji Star, Harami Cross, Kicking Bull/Bear, Ladder Bottom, Long-Legged Doji, Mat Hold, Rising/Falling Three Methods, Three Outside Up/Down — with Polish `indication` and `detailed_description` for each
- `indication`, `reliability` (★–★★★, int 1–3) and `detailed_description` fields on `PatternDetection` model (Pydantic + TypeScript); backward-compatible defaults for all non-candlestick detectors
- Multi-candle scanning: `detect_candlestick_patterns` now scans last 10 candles (was: last candle only); `location` field set to `"emerging"` (last candle) or `"completed"` (older); duplicate suppression per pattern × candle index
- `RELIABILITY_MULTIPLIER` constant (`{1: 1.0, 2: 1.3, 3: 1.6}`) in `core/models.py`; used in `normalize_pattern_signal()` (aggregator) and `_pattern_confirmation()` (confidence scorer) — patterns with higher reliability get proportionally larger weight
- Confirming patterns (★★+, same direction, candlestick category) appended to `entry_condition` text in `calculate_entry_points()` via new `confirming_patterns` parameter; `report_builder` filters and passes them
- `PatternDetailModal` component — modal opened on pattern row click showing name, direction badge, reliability stars, indication, Polish description, confidence bar, and candle index; closes on Escape key, X button, or overlay click; `role="dialog"`, `aria-modal="true"` (WCAG)
- Reliability stars (★/★★/★★★) rendered in `PatternRow` next to direction badge
- 4 new E2E tests for `PatternDetailModal` (`pattern-detail-modal.spec.ts`): open on click, close on Escape, close on X button, WCAG aria attributes
- 21 new backend unit tests covering: 28-pattern dictionary completeness, multi-candle scanning, reliability/confidence mapping, indication direction, deduplication, `RELIABILITY_MULTIPLIER` effect in aggregator and confidence scorer, `entry_condition` confirming patterns text

- Support for 15 new CFD instruments across all layers: 7 PLN forex pairs (EURPLN, USDPLN, GBPPLN, CHFPLN, JPYPLN, AUDPLN, CADPLN), 5 commodities (COFFEE, COPPER, PLATINUM, PALLADIUM, OILWTI) and W20 index — instrument classifier, all three data providers (YFinance, TwelveData, FMP) and frontend autocomplete suggestions
- Architecture tests enforcing COMMODITY_SYMBOLS and INDEX_SYMBOLS consistency across all data provider symbol maps; fixes pre-existing gaps for BRENT, NATGAS, COPPER, PLATINUM and PALLADIUM
- Unit tests for COFFEE (commodity, not forex via 6-char heuristic), EURPLN, OILWTI and W20 classification

- Price pattern filtering by category in `PatternList` component — tab bar with five categories (Świecowe, Wykresowe, S/R, Fibonacci, IKI) plus "Wszystkie" aggregate view; default shows top 5 patterns with expand toggle
- `PatternCategory` enum (`candlestick`, `chart_pattern`, `support_resistance`, `fibonacci`, `iki`) in `core/models.py` — all five detectors now set `category` and `detected_at_index` on every `PatternDetection`
- `relevance_scorer` module with `score_patterns()` (formula: 0.5 × confidence + 0.35 × recency + 0.15 × proximity) and `calculate_target_prices()` (ATR-based per category); patterns sorted by `relevance_score` DESC in both pipeline and `/patterns` endpoint
- Staleness indicator in `PatternList` — shows "X świec temu" badge when `detected_at_index` is available
- Target price display per pattern row with color coding (bullish green / bearish red)
- Chart markers positioned at `detected_at_timestamp` instead of the last candle — markers sorted by time ascending (required by lightweight-charts v5 API)
- Dashed target price line on chart when a pattern is selected in `PatternList`
- `detected_at_timestamp` and `relevance_score` and `target_price` fields added to `PatternDetection` Pydantic model and TypeScript `PatternDetection` interface

- CA CPI (`CPALTT01CAM659N`), US CPI (`CPALTT01USM659N`) and CH CPI (`CPALTT01CHM659N`) added to `SERIES_LOOKBACK_DAYS` with 540-day windows — all OECD MEI CPI series on FRED stopped updating since May 2025 ("Next Release Date: Not Available"); the default 365-day window excluded their last observations (Mar/Apr 2025), causing `inflation_yoy = null` and `inflation_differential = null` for 17 of 26 supported forex pairs (65%), including all USD, CAD and CHF majors
- AUD CPI (`CPALTT01AUQ659N`) added to `SERIES_LOOKBACK_DAYS` with a 540-day window, matching the NZ CPI override — the default 365-day window excluded the Q1 2025 observation (dated 2025-01-01) from April 2026 onward, causing `AUD_inflation_yoy = null` for AUD/NZD pairs
- `_compute_inflation_differential()` and `_compute_rate_differential()` now return `None` instead of `0.0` when either component is missing — the UI correctly displays "–" instead of the misleading "0"

- Support for 5 NZD cross pairs (NZDJPY, NZDCAD, NZDCHF, EURNZD, GBPNZD) across all layers: instrument classifier, three data providers (YFinance, TwelveData, FMP), fundamental analysis pair mapping, and frontend autocomplete suggestions
- R/R (TP2) column in entry strategies table — second Risk/Reward ratio calculated against TP2 (aspirational target) alongside existing R/R (TP1); reuses `formatRiskReward` / `riskRewardClass` helpers; column headers renamed from "Risk/Reward" to "R/R (TP1)" and "R/R (TP2)"
- Risk/Reward column in entry strategies table — displays ratio in trading-standard `1:X.XX` format with color coding (green ≤ 0.5, yellow 0.5–1.0)
- Backend R/R calculation (`_calculate_risk_reward`) using TP1 as reward target
- Automatic filtering of strategies with unfavorable risk/reward ratio (R/R > 1.0) — filtered strategies are removed from the report
- Skip reason message when all strategies are filtered out due to unfavorable R/R
- Unit tests for R/R calculation (favorable, unfavorable, boundary, None, zero reward) and filtering logic
- Badge bar in README.md (Python, FastAPI, Next.js, Docker, Version, License) matching SeqMcpServer style
- Horizontal rule separators between README sections for visual consistency
- Security and Changelog footer sections in README.md
- Support for AUDNZD forex pair across all layers: instrument classifier, three data providers (YFinance, TwelveData, FMP), frontend suggestions
- NZD macro data for fundamental analysis: RBNZ interest rate (`IRSTCI01NZM156N`) and NZ CPI (`CPALTT01NZQ659N`) FRED series
- NZD currency maps in forex analyzer (`CURRENCY_RATE_MAP`, `CURRENCY_CPI_MAP`) — also fixes NZDUSD fundamental analysis returning score=0
- Unit tests for AUDNZD fundamental analysis (happy path + missing data)
- GitHub Discussions contact link in issue template config — directs users to Discussions before opening issues
- Support for 10 forex cross pairs (AUDCAD, AUDCHF, AUDJPY, CADJPY, CHFJPY, EURCHF, EURAUD, EURCAD, GBPCAD, GBPCHF) in all data providers and frontend suggestions
- Architecture test enforcing FOREX_PAIRS consistency across all data provider symbol maps

- `FredSource.fetch_series()` now retries transient FRED API errors (OSError, including ConnectionError and TimeoutError subclasses) with exponential backoff via tenacity (3 attempts, 1–10s wait); permanent errors (ValueError) and empty-data responses are not retried; improves reliability for GBP CPI and NZD interest rate data
- Add Git Workflow section to `copilot-instructions.md` — branching strategy (semver branches + merge-forward), commit conventions, pre-commit checklist

- Replace discontinued FRED overnight interbank rate series for NZD (`IRSTCI01NZM156N`, last obs Dec 2024) and CHF (`IRSTCI01CHM156N`, last obs Mar 2024) with active 3-month interbank rate series (`IR3TIB01NZM156N`, `IR3TIB01CHM156N`) — restores NZD_interest_rate and CHF_interest_rate fields in fundamental analysis for all NZD and CHF pairs
- Add lookback override of 540 days for UK CPI series (`CPALTT01GBM659N`) to account for OECD publication lag (~6 weeks)
- Fix null NZ inflation data caused by discontinued FRED series `CPALTT01NZQ659N` — switch to `NZLCPIALLQINMEI` (quarterly index) with FRED `units=pc1` transformation
- Offload CPU-intensive technical analysis and pattern recognition to thread pool (`asyncio.to_thread`) — prevents blocking the async event loop which caused Gateway Timeout on health checks and stalled WebSocket progress updates

- Replace discontinued/unavailable FRED CPI series: US (`CPIAUCSL` → `CPALTT01USM659N` YoY%), JP (`CPALTT01JPM659N` → `FPCPITOTLZGJPN` annual IMF), AU (`CPALTT01AUM659N` → `CPALTT01AUQ659N` quarterly OECD)
- Add `SERIES_YOY_UNITS` dict to convert EU HICP index to YoY% via FRED `units=pc1` parameter
- Add `SERIES_LOOKBACK_DAYS` dict for per-series lookback overrides (730 days for annual JP CPI)
- Rewrite index inflation scoring to use CPI YoY% deviation from 2% target instead of skipping CPI index values
- Rewrite commodity real-rate scoring to compute actual real rate (`fed_rate - cpi_yoy`) instead of heuristic
- Rename forex fundamental indicators from `_cpi` to `_inflation_yoy` and display inflation differential in percentage points

- Fix "Brak danych rynkowych" error for 10 forex cross pairs (AUDCAD etc.) — add missing symbol mappings to YFinance, TwelveData and FMP providers
- Fix null inflation data for JPY and AUD currency pairs caused by discontinued FRED OECD series
- Fix EU inflation always null — add FRED `units=pc1` parameter to convert Eurostat HICP index to YoY%
- Fix US CPI returning raw index value instead of YoY% — switch from `CPIAUCSL` (SA index) to `CPALTT01USM659N` (YoY%)
- Fix Docker healthchecks failing inside containers — replace `localhost` with `127.0.0.1` in `wget` commands
- Fix backend entrypoint `exec format error` on Linux — strip Windows CRLF line endings in Dockerfile
- Fix Next.js standalone server not accepting external connections — set `HOSTNAME=0.0.0.0` in frontend Dockerfile

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

- Extend default data period from 90 to 200 days for improved indicator accuracy
- Parameterize all 9 existing indicators via preset configuration instead of hardcoded values
- Indicator names now reflect active parameters (e.g., `CCI(14)` for Investing, `CCI(20)` for TradingView)

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

- Unreachable timeframe validation in `analysis.py` removed (Pydantic handles at deserialization)
- Removed unused `CURRENCYLAYER_API_KEY` and `MARKETSTACK_API_KEY` from Settings
- Removed unused `DataCache` protocol from `cache.py`
- Removed unused logging import from `interfaces.py`
- Removed unused `slowapi` and `websockets` from active dead-code (slowapi now active)
- WebSocket `onmessage` now logs parse errors instead of silently swallowing them

- Resolve 36 mypy strict-mode errors: list variance, nullable arithmetic, NDArray types, unused type:ignore suppressions
- Fix chart pattern test data generators to produce oscillating data for `argrelextrema` peak/trough detection
- Fix `fred_source.py` returning untyped cached value (`Any`) instead of `float`

- Project foundation: FastAPI app, Pydantic settings, async SQLAlchemy with SQLite
- Domain models: 7 enums and 11 Pydantic models for OHLCV, indicators, signals
- Database layer with Alembic migrations
- Docker and Docker Compose setup
- CI pipeline with pytest, ruff, and mypy
- Health check endpoint: `GET /api/v1/health`
