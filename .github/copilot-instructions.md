This file is the project constitution — the single source of truth for architecture, tech stack, and fundamental coding conventions. Every rule below is a hard constraint. When in doubt, these instructions take precedence over general knowledge or external best practices.

# Architecture

Modular monolithic system for investment analysis: Python/FastAPI backend + Next.js frontend.

Backend (`backend/app/`) has three layers:

- `api/v1/` — versioned REST endpoints, one router per domain
- `core/` — cross-cutting concerns: config, database, models, auth, rate limiting, logging, instrument classification
- `modules/` — six independent domain modules: `data_acquisition`, `technical_analysis`, `pattern_recognition`, `fundamental_analysis`, `signal_aggregation`, `strategy_generator`

Frontend (`frontend/src/`) — Next.js App Router, single-page application.

Infrastructure — Docker Compose (nginx + backend + frontend), CI via GitHub Actions.

**Import boundaries (enforced by import-linter):**

- Domain modules MUST NOT import from each other — communicate only via Pydantic models in `core/models.py`.
- `core/` MUST NOT import from `modules/` or `api/`.
- `api/` may import from `core/` and `modules/`.

# Tech Stack

## Backend

- Python >=3.12,<3.14 (target: py313)
- FastAPI >=0.115, Pydantic >=2.10, pydantic-settings >=2.7
- SQLAlchemy >=2.0 (async, DeclarativeBase + Mapped/mapped_column)
- Alembic >=1.14 (async runner), SQLite via aiosqlite (MVP)
- pandas >=2.2, pandas-ta, TA-Lib, scipy
- httpx (external APIs), cachetools (TTLCache), slowapi (rate limiting)
- yfinance (primary data provider), fredapi (macro data via FRED), websockets >=14.0 (real-time analysis updates)
- ruff >=0.8 (format + lint, line-length=120), mypy >=1.13 (strict)
- pytest >=8.3, pytest-asyncio (auto mode), pytest-cov, coverage threshold 80%

## Frontend

- Next.js 14.2.35 (App Router, standalone output)
- React 18, TypeScript 5 (strict mode)
- Tailwind CSS 3.4.1 with custom CSS variables (dark theme tokens)
- lightweight-charts 5.1 (TradingView)
- Playwright 1.58, @axe-core/playwright (E2E + a11y)
- Prettier 3.8, ESLint 8 + eslint-config-next + eslint-config-prettier

# Coding Conventions

Rules NOT enforced by linters — do not duplicate ruff, mypy, ESLint, or Prettier rules.

## Backend

Use app factory pattern: `create_app()` in `main.py` with lazy router imports inside the factory.

Config singleton via pydantic-settings `BaseSettings` + `@lru_cache` in `get_settings()`.

All enums use `StrEnum` — never string literals or old-style `Enum`.

Pydantic v2 syntax only: `model_config = SettingsConfigDict(...)`, not inner `class Config`.

SQLAlchemy 2.0 style only: `Mapped[type]`, `mapped_column()`, `DeclarativeBase`.

Protocol-based DI: `DataProvider` is a `@runtime_checkable Protocol`.

Async-first: all I/O operations must be async.

Module logging: `logging.getLogger(__name__)` in every module.

Redact sensitive data in logs using `_SENSITIVE_KEYS`.

Domain modules are orchestrated by a 6-step `AnalysisPipeline`.

Fallback chain pattern for data providers: YFinance → TwelveData → FMP.

```python
# Preferred: StrEnum
class AssetType(StrEnum):
    STOCK = "stock"
    ETF = "etf"

# Avoid: string literals or old Enum
asset_type: str = "stock"  # no
```

```python
# Preferred: Pydantic v2 config
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

# Avoid: inner class Config
class Settings(BaseSettings):
    class Config:  # no
        env_file = ".env"
```

## Frontend

Add `"use client"` directive on interactive components.

Type props as `Readonly<Props>` — not plain `Props`.

Use default exports for components.

Path alias: `@/*` maps to `./src/*`.

UI strings are in Polish (`lang="pl"`). Error messages use `"Błąd:"` prefix.

Dark theme via CSS custom properties — not Tailwind `dark:` modifier.

Dynamic imports with `next/dynamic` + `{ ssr: false }` for chart components — because lightweight-charts requires browser APIs.

No external state library — pure React hooks only.

Centralized API layer in `src/lib/api.ts`: `apiFetch<T>` wrapper + WebSocket helper.

Types in `src/types/index.ts` mirror backend Pydantic models.

```tsx
// Preferred: Readonly props + default export
interface Props { readonly symbol: string }
export default function StockCard({ symbol }: Readonly<Props>) { ... }

// Avoid: mutable props + named export
export function StockCard({ symbol }: { symbol: string }) { ... }
```

# Error Handling

Backend: raise `HTTPException` with specific status codes — 400 bad input, 404 not found, 502 upstream failure.

Use `DataProviderError` for fallback chain failures.

Validate input via regex patterns in `validators.py`, raising `HTTPException(400)` on mismatch.

Rate limiting: slowapi decorators per endpoint + `DailyRateLimiter` for external API quotas.

Frontend: prefix all user-facing error messages with `"Błąd:"`.

Never expose internal error details in API responses.

# Testing Strategy

## Backend

Unit tests: pytest functions (no classes), `test_<behavior>` naming.

Integration tests: class-based (`TestXxx`), use `client` fixture (httpx `AsyncClient` via `ASGITransport`).

Shared fixtures in `conftest.py`: `async_engine` (in-memory SQLite), `db_session`, `client`, `sample_ohlcv_data`.

Helper factory: `make_ohlcv()` in `tests/helpers.py`.

Architecture tests: import-linter enforcement via `test_import_boundaries.py`.

Markers: `@pytest.mark.integration`, `@pytest.mark.architecture`.

All async tests use pytest-asyncio auto mode — no explicit `@pytest.mark.asyncio` needed.

## Frontend E2E

Playwright fixtures in `e2e/fixtures.ts` — `mockAnalysisApi()` intercepts HTTP + WebSocket.

Accessibility-first selectors: `getByRole()`, `getByText()` — never `data-testid` first.

axe-core audits for WCAG 2.1 AA compliance (zero critical+serious violations).

Chromium only in CI.

# Developer Workflow

```bash
# Full stack (Docker)
docker compose up                          # nginx + backend + frontend

# Backend standalone
cd backend && uvicorn app.main:app --reload  # requires activated venv

# Frontend standalone
cd frontend && npm run dev

# Backend tests
cd backend && pytest

# Frontend E2E
cd frontend && npx playwright test

# Linting
cd backend && ruff check . && ruff format --check .
cd frontend && npm run lint

# Type checking
cd backend && mypy app/

# Database migrations
cd backend && alembic upgrade head
```

Environment: `.env` file in `backend/` (copy from `.env.example`). API keys are optional — yfinance works without them.

CI: GitHub Actions with 6 jobs — lint, type-check, test, security, frontend-lint, frontend-e2e.
