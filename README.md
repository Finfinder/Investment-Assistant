# Investment Assistant

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Version](https://img.shields.io/badge/version-0.3.0-green)]()
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=Finfinder_Investment-Assistant&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Finfinder_Investment-Assistant)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CFD instrument technical and fundamental analysis application. Provides market data retrieval with multi-provider fallback, technical indicators, and analysis endpoints via a REST API.

## Feedback, Issues, and Contributing

- Report bugs and feature ideas through GitHub Issues: https://github.com/Finfinder/Investment-Assistant/issues
- Larger goals are tracked with milestones and the pinned roadmap issue.
- Collaboration notes live in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Tech Stack

### Backend

- **Python 3.13** / FastAPI / Pydantic 2
- **SQLAlchemy 2** (async, SQLite for MVP)
- **Redis** (caching with fallback to in-memory)
- **Data providers**: yfinance (primary), Twelve Data, Financial Modeling Prep
- **Analysis**: pandas-ta, TA-Lib

### Frontend

- **Next.js 14** (App Router) / TypeScript 5
- **TailwindCSS 3.4** with CSS custom properties (dark theme)
- **lightweight-charts v5** for interactive candlestick charts
- **Docker Compose** for full-stack deployment

---

## Quick Start

### Prerequisites

- Python 3.12–3.13
- [TA-Lib C library](https://ta-lib.org/) installed on the system

### Local Development

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API keys (optional — yfinance works without keys)

uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000`.

### Docker (recommended)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

docker compose up --build
```

The application is available at `http://localhost` (nginx reverse proxy). Health check: `GET /api/v1/health`. API documentation: `http://localhost/api/v1/docs`.

The local `docker compose` stack builds the same `backend`, `frontend`, and `nginx` Dockerfiles that are published during tagged releases.

---

## Release Artifacts

Tagged releases publish three container images to GHCR:

- `ghcr.io/<owner>/<repo>-backend`
- `ghcr.io/<owner>/<repo>-frontend`
- `ghcr.io/<owner>/<repo>-nginx`

Each image is published with a semver tag matching the release, an immutable `sha-<commit>` tag, and `latest` only for stable tags without a prerelease suffix.

GitHub Release notes are generated from `CHANGELOG.md`. The supported release artifacts are container images only; this repository does not publish a frontend npm package or a backend PyPI package.

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │      │   Backend    │      │    Redis     │
│  Next.js 14  │◄────►│  FastAPI     │◄────►│   Cache      │
│  :3000       │      │  :8000       │      │   :6379      │
└──────┬───────┘      └──────┬───────┘      └──────────────┘
       │                     │
       └────────┬────────────┘
                │
         ┌──────▼──────┐
         │   nginx     │
         │   :80       │
         └─────────────┘
```

The backend is organized into independent domain modules that communicate through core models:

```
backend/app/
├── api/v1/          # REST + WebSocket endpoints
├── core/            # Settings, database, shared models, logging
└── modules/
    ├── data_acquisition/      # Multi-provider market data (yfinance, Twelve Data, FMP)
    ├── technical_analysis/    # 9 oscillators, 12 MAs, 5 pivot types
    ├── pattern_recognition/   # Candlestick, S/R, Fibonacci, IKI, geometric
    ├── fundamental_analysis/  # Forex/commodity/index macro analysis (FRED, OECD SDMX, BLS, StatCan, BFS, FMP)
    ├── signal_aggregation/    # Weighted signal scoring and consolidation
    └── strategy_generator/    # Entry/exit scenarios with SL/TP levels
```

Import boundaries are enforced by `import-linter` contracts defined in `pyproject.toml`.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/market-data/{symbol}` | Fetch OHLCV data for a CFD symbol |
| POST | `/api/v1/technical-analysis` | Run full technical analysis |
| POST | `/api/v1/patterns` | Detect chart and candlestick patterns |
| POST | `/api/v1/fundamental-analysis` | Run fundamental analysis for a symbol |
| POST | `/api/v1/analysis` | Trigger full analysis pipeline (async) |
| GET | `/api/v1/analysis/{id}` | Get analysis result or status |
| GET | `/api/v1/analysis/{id}/status` | Get analysis progress status |
| WS | `/api/v1/ws/analysis/{id}` | WebSocket for live status updates |

### Market Data

```
GET /api/v1/market-data/EURUSD?timeframe=H1&period=30d
```

Supported symbols include forex pairs (EURUSD, GBPUSD, …), commodities (GOLD, SILVER, …), indices (US500, US30, …), and more. Timeframes: M15, H1, H4, D1. Period format: `{n}d`, `{n}m`, `{n}y`.

### Technical Analysis

```
POST /api/v1/technical-analysis
{"symbol": "EURUSD", "timeframe": "H1", "period": "90d"}
```

Returns 9 oscillator/momentum indicators (RSI, MACD, Stochastic, CCI, ADX, AO, Momentum, Williams %R, Ultimate Oscillator), 12 moving averages (SMA + EMA for periods 5–200), 5 pivot point types (Classic, Fibonacci, Camarilla, Woodie, DeMark), and an aggregated signal summary.

### Pattern Recognition

```
POST /api/v1/patterns
{"symbol": "EURUSD", "timeframe": "H1", "period": "180d"}
```

Detects candlestick patterns (28 types via TA-Lib, scanned across last 10 candles) with reliability rating (★–★★★), signal indication and Polish description. Also detects support/resistance levels with strength scoring, Fibonacci retracement levels, IKI (Impulse-Correction-Impulse) patterns, and geometric chart patterns (triangle, wedge, flag, pennant).

### Fundamental Analysis

```
POST /api/v1/fundamental-analysis
{"symbol": "EURUSD"}
```

Automatically routes to the correct analyzer based on instrument type. Forex pairs compare interest rate and inflation differentials between base and quote currencies. Commodities analyze COT positioning, USD strength, and rate environment. Indices evaluate regional macro data (rates, unemployment). Data sourced from FRED API, OECD SDMX (monthly Japan CPI YoY), country CPI fallback APIs (BLS for US, Statistics Canada for CA, BFS/FSO for CH), and Financial Modeling Prep.

### Full Analysis Pipeline

```
POST /api/v1/analysis
{"symbol": "EURUSD", "timeframe": "H1"}
```

Triggers an asynchronous 6-step pipeline: data fetch → technical analysis → pattern recognition → fundamental analysis → signal aggregation → strategy generation. Returns an `analysis_id` to poll via `GET /api/v1/analysis/{id}` or subscribe via `WS /api/v1/ws/analysis/{id}` for live progress updates. The final report includes weighted signal scoring, entry point scenarios (aggressive and conservative), SL/TP levels, and confidence percentages.

---

## Configuration

Copy `backend/.env.example` to `backend/.env`. For production see `.env.production.example`.

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite+aiosqlite:///./data/investment.db` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `TWELVE_DATA_API_KEY` | Twelve Data API key (optional) | — |
| `FMP_API_KEY` | Financial Modeling Prep API key (optional) | — |
| `FRED_API_KEY` | FRED API key (optional) | — |
| `CACHE_TTL_INTRADAY` | Cache TTL for intraday data (seconds) | `300` |
| `CACHE_TTL_DAILY` | Cache TTL for daily data (seconds) | `3600` |

---

## Testing

```bash
# Backend — unit & integration tests
cd backend
python -m pytest tests/ -v

# Architecture boundary checks
lint-imports

# Frontend lint & type-check
cd frontend
npm run lint
npm run build

# E2E tests (requires running frontend)
cd frontend
npm run test:e2e

# Performance tests (requires k6 CLI)
k6 run tests/performance/analysis.k6.js
```

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

---

## Security

To report a security vulnerability, please see [SECURITY.md](SECURITY.md) for instructions.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

---

## License

This project is licensed under the [MIT License](LICENSE).

