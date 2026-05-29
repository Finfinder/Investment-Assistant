# Contributing to Investment Assistant

Thank you for your interest in contributing to Investment Assistant! This guide will help you get started with the project setup, understand our conventions, and submit high-quality contributions.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior through the channels described in the Code of Conduct.

## Security

If you discover a security vulnerability, **do NOT open a public issue**. Instead, report it privately through [GitHub Security Advisories](https://github.com/Finfinder/Investment-Assistant/security/advisories/new). See [SECURITY.md](SECURITY.md) for details.

## Issues, Roadmap, and Linking

- Report bugs and feature requests through GitHub Issues: https://github.com/Finfinder/Investment-Assistant/issues
- Larger goals are tracked with milestones and the pinned `Project Status / Roadmap` issue.
- Link related work in commits and pull requests with `Refs #123`, `Fixes #123`, or `Closes #123`.
- For pull requests targeting version branches, prefer `Refs #123` unless the branch change is intended to fully close the issue there.
- Keep commit subjects aligned with this repository's existing conventions and instructions instead of forcing a global commit style.

## Getting Started

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Python](https://www.python.org/downloads/) | 3.12+ | Target: 3.13 |
| [Node.js](https://nodejs.org/) | 20.x | For frontend |
| [TA-Lib C library](https://ta-lib.org/) | Latest | Required for technical indicators (see below) |
| [Git](https://git-scm.com/) | Latest | |
| [Docker](https://www.docker.com/) | Latest | Optional — for full-stack deployment |

#### Installing TA-Lib

TA-Lib requires the C library to be installed before the Python wrapper:

**Windows:**
Download the pre-built binary from [TA-Lib releases](https://github.com/ta-lib/ta-lib/releases) and extract to `C:\ta-lib`. Ensure `C:\ta-lib\lib` is in your system PATH.

**macOS:**
```bash
brew install ta-lib
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y build-essential wget
wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz
tar -xzf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4
./configure --prefix=/usr
make
sudo make install
```

### Clone and Build

```bash
git clone https://github.com/Finfinder/Investment-Assistant.git
cd Investment-Assistant

# Backend
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env

# Frontend
cd ../frontend
npm ci
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_NAME` | Application name | No (default: `Investment Assistant`) |
| `DEBUG` | Enable debug mode | No (default: `true`) |
| `API_V1_PREFIX` | API version prefix | No (default: `/api/v1`) |
| `LOG_LEVEL` | Logging level | No (default: `DEBUG`) |
| `DATABASE_URL` | SQLAlchemy database URL | No (default: SQLite) |
| `TWELVE_DATA_API_KEY` | Twelve Data API key | No — optional fallback provider |
| `FMP_API_KEY` | Financial Modeling Prep API key | No — optional fallback provider |
| `FRED_API_KEY` | FRED API key | No — for fundamental analysis |
| `CACHE_TTL_INTRADAY` | Cache TTL for intraday data (seconds) | No (default: `300`) |
| `CACHE_TTL_DAILY` | Cache TTL for daily data (seconds) | No (default: `3600`) |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | No (default: `["http://localhost:3000"]`) |

> **Note:** yfinance (primary data provider) works without any API keys.

### Running the Application

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Full stack (Docker)
docker compose up
```

## Project Structure

```
backend/app/
├── api/v1/          # Versioned REST + WebSocket endpoints (one router per domain)
├── core/            # Cross-cutting concerns: config, database, models, auth, logging
└── modules/
    ├── data_acquisition/      # Multi-provider market data (yfinance → Twelve Data → FMP)
    ├── technical_analysis/    # Oscillators, moving averages, pivot points
    ├── pattern_recognition/   # Candlestick, S/R, Fibonacci, IKI, geometric patterns
    ├── fundamental_analysis/  # Forex/commodity/index macro analysis (FRED, FMP)
    ├── signal_aggregation/    # Weighted signal scoring and consolidation
    └── strategy_generator/    # Entry/exit scenarios with SL/TP levels

frontend/src/
├── app/             # Next.js App Router pages
├── components/      # React components
├── lib/             # API client, utilities
└── types/           # TypeScript types (mirror backend Pydantic models)
```

### Import Boundaries

Domain modules (`backend/app/modules/*`) are **independent** — they must NOT import from each other. Communication between modules happens exclusively via shared Pydantic models in `core/models.py`. These boundaries are enforced by `import-linter` contracts defined in `pyproject.toml`.

```
core/       → MUST NOT import from modules/ or api/
modules/*   → MUST NOT import from each other
api/        → MAY import from core/ and modules/
```

## Coding Conventions

For complete coding conventions, see [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

### Backend

- **Enums**: Use `StrEnum` — never string literals or old-style `Enum`
- **Pydantic**: v2 syntax only — `model_config = SettingsConfigDict(...)`, not inner `class Config`
- **SQLAlchemy**: 2.0 style — `Mapped[type]`, `mapped_column()`, `DeclarativeBase`
- **Async-first**: All I/O operations must be async
- **DI**: Protocol-based — `DataProvider` is a `@runtime_checkable Protocol`
- **Logging**: `logging.getLogger(__name__)` in every module
- **Error handling**: `HTTPException` with status codes 400 (bad input), 404 (not found), 502 (upstream failure)
- **Linting**: ruff (format + lint, line-length=120)
- **Type checking**: mypy (strict mode)

### Frontend

- **Directives**: `"use client"` on interactive components
- **Props**: Type as `Readonly<Props>`, use default exports
- **Styling**: CSS custom properties for dark theme — not Tailwind `dark:` modifier
- **Accessibility**: WCAG 2.1 AA compliance required
- **State**: Pure React hooks only — no external state library
- **Linting**: ESLint + Prettier

### What NOT to Do

| Anti-pattern | Correct approach |
|-------------|-----------------|
| Import between domain modules | Communicate via `core/models.py` |
| String literals for enum values | Use `StrEnum` |
| `class Config` in Pydantic models | Use `model_config = SettingsConfigDict(...)` |
| Named exports for components | Use default exports |
| Tailwind `dark:` modifier | Use CSS custom properties |
| Synchronous I/O in backend | Use async equivalents |

## Adding Features

### Adding a New API Endpoint

1. Create a new router in `backend/app/api/v1/`
2. Define request/response Pydantic models in `core/models.py`
3. Register the router in the `create_app()` factory in `main.py`
4. Add input validation using shared patterns from `core/validators.py`
5. Add rate limiting via `slowapi` decorators

See existing routers (e.g., `analysis.py`, `market_data.py`) as reference implementations.

### Adding a New Domain Module

1. Create a new directory under `backend/app/modules/`
2. Implement the module using only `core/` imports — never import from other modules
3. Define shared data models in `core/models.py`
4. Wire into the `AnalysisPipeline` if the module participates in the analysis flow
5. Add import-linter contract in `pyproject.toml`

See `technical_analysis` and `data_acquisition` modules as reference implementations.

> **Important:** Import boundaries are a hard constraint enforced by `import-linter` and tested in CI. Violations will fail the build.

## Testing

### Backend

```bash
cd backend

# Run all tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage report
pytest --cov=app --cov-branch
```

**Conventions:**
- **Unit tests**: pytest functions (no classes), `test_<behavior>` naming
- **Integration tests**: class-based (`TestXxx`), use `client` fixture (httpx `AsyncClient`)
- **Markers**: `@pytest.mark.integration`, `@pytest.mark.architecture`
- **Coverage threshold**: 80% (enforced in CI)
- **Test helpers**: `make_ohlcv()` factory in `tests/helpers.py`

### Frontend E2E

```bash
cd frontend

# Run all E2E tests
npx playwright test
```

**Conventions:**
- Playwright + `@axe-core/playwright` for accessibility audits
- Accessibility-first selectors: `getByRole()`, `getByText()` — never `data-testid` first
- Chromium only in CI
- Mock fixtures in `e2e/fixtures.ts`

### Linting and Type Checking

```bash
# Backend
cd backend
ruff check .                    # Lint
ruff format --check .           # Format check
mypy app/                       # Type checking

# Frontend
cd frontend
npm run lint                    # ESLint + Prettier
```

## Git Workflow

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/). All commit messages must be in English, imperative mood.

**Types:**
| Type | Description |
|------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `style:` | Formatting, missing semicolons, etc. (no code change) |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance tasks (dependencies, configs) |
| `ci:` | CI/CD pipeline changes |

**Examples:**
```
feat: add Fibonacci retracement detection
fix: correct RSI calculation for edge case
docs: update API endpoint documentation
test: add integration tests for market data fallback
ci: add pip-audit security scanning job
```

### Branch Strategy

This project uses **version branches** (e.g., `0.1.1`, `0.2.0`). When submitting a PR, target the **highest active version branch**.

### Before Committing

1. Run tests: `cd backend && pytest`
2. Run linting: `cd backend && ruff check . && ruff format --check .`
3. Run type checking: `cd backend && mypy app/`
4. Run frontend lint: `cd frontend && npm run lint`
5. Update `CHANGELOG.md` under `[Unreleased]`
6. Update `README.md` if your change affects user-facing documentation

## Submitting a Pull Request

1. **Fork** the repository and create a branch from the highest version branch
2. **Implement** your changes following the conventions above
3. **Test** your changes thoroughly
4. **Commit** using Conventional Commits format
5. **Open a PR** against the target version branch

### PR Checklist

Before submitting, ensure:

- [ ] Backend tests pass (`cd backend && pytest`)
- [ ] Type checking passes (`cd backend && mypy app/`)
- [ ] Linting passes (`cd backend && ruff check . && ruff format --check .`)
- [ ] Frontend lint passes (`cd frontend && npm run lint`)
- [ ] Frontend E2E tests pass (`cd frontend && npx playwright test`) — if frontend changes
- [ ] No known dependency vulnerabilities (`cd backend && pip-audit`)
- [ ] New functionality has unit tests
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `README.md` updated (if applicable)
- [ ] No hardcoded credentials or API keys
- [ ] Import boundaries respected (modules don't import from each other)
- [ ] Security review completed (no OWASP Top 10 issues, inputs validated)
- [ ] Code follows project conventions

## Reporting Issues

Use the [issue templates](https://github.com/Finfinder/Investment-Assistant/issues/new/choose) to report bugs or request features. Please fill out all required fields to help us address your issue efficiently.
