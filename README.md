# Investment Assistant

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Version](https://img.shields.io/badge/version-0.5.1-green)]()
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

- **Next.js 15** (App Router) / TypeScript 5
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

All three base images are pinned by their `@sha256` digest (build arguments `NODE_IMAGE_DIGEST` in `frontend/Dockerfile`, `PYTHON_IMAGE_DIGEST` in `backend/Dockerfile`, and `NGINX_IMAGE_DIGEST` in `nginx/Dockerfile`) to guard against supply-chain attacks and ensure reproducible builds (IA-163 / #220, IA-164 / #222). The digests are the single source of truth, so `release.yml` and `docker-compose.yml` inherit them without passing build arguments. Rotate a digest when its upstream image is rebuilt with a security fix:

```bash
docker buildx imagetools inspect node:$(cat frontend/.nvmrc)-alpine   # frontend
docker buildx imagetools inspect python:3.12-slim                              # backend
docker buildx imagetools inspect nginx:1.27-alpine                              # nginx
# use the value from the "Digest:" line (manifest list / index digest)
```

GitHub Release notes are generated from `CHANGELOG.md`. The supported release artifacts are container images only; this repository does not publish a frontend npm package or a backend PyPI package.

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │      │   Backend    │      │    Redis     │
│  Next.js 15  │◄────►│  FastAPI     │◄────►│   Cache      │
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

## Deployment Architecture

The application is deployed as a single Docker Compose stack of four services. `nginx` is the only service publishing a port to the host; `backend`, `frontend` and `redis` communicate exclusively over the internal Compose network.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Docker Compose Stack                         │
│                                                                        │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│   │    nginx     │    │   backend    │    │        redis         │    │
│   │ :80 (host)   │───►│   :8000      │───►│        :6379         │    │
│   │ reverse proxy│    │   FastAPI    │    │        cache         │    │
│   └──────┬───────┘    └──────┬───────┘    └──────────────────────┘    │
│          │                   │                                         │
│          │      ┌────────────▼────────────┐                           │
│          └─────►│        frontend          │                           │
│                 │        :3000             │                           │
│                 │        Next.js 15        │                           │
│                 └──────────────────────────┘                           │
│                                                                        │
│   Volumes:  redis-data  │  backend-data  │  nginx-logs                │
└──────────────────────────────────────────────────────────────────────┘
```

`nginx` terminates all inbound traffic on `:80` and proxies `/api/` and `/api/v1/ws/` to `backend:8000`, while everything else is served by `frontend:3000`. `redis` is reached **only by the backend** (the `nginx → backend → redis` arrow in the diagram denotes the backend's cache dependency, not a direct proxy path from nginx). `backend` depends on `redis:6379` for caching (with in-memory fallback). Startup order is enforced by `depends_on` conditions: `redis` (healthy) → `backend` (healthy) → `frontend` (started) → `nginx`. Note that `nginx.depends_on.frontend` uses `condition: service_started` (not a health condition), while the other dependencies wait on `service_healthy`.

> **Production note:** the stack terminates plain HTTP on `:80`. The HTTPS redirect in `nginx/nginx.conf` is commented out and must be enabled (with TLS certificates provisioned) before exposing the stack to production traffic. See the [Security](#security) section for the security headers applied at the proxy layer.

### Port mappings

| Service | Container port | Published to host | Notes |
|---|---|---|---|
| nginx | 80 | Yes (`:80`) | Only externally reachable entry point |
| backend | 8000 | No | Internal only, behind nginx |
| frontend | 3000 | No | Internal only, behind nginx |
| redis | 6379 | No | Internal only, protected by `REDIS_PASSWORD` |

### Volumes

| Volume | Mount point | Purpose |
|---|---|---|
| `redis-data` | `/data` (redis) | Persistent Redis cache data |
| `backend-data` | `/app/data` (backend) | Persistent backend data (SQLite DB, etc.) |
| `nginx-logs` | `/var/log/nginx` (nginx) | Nginx access/error logs |

### Healthchecks

| Service | Check | Interval | Timeout | Retries | Start period |
|---|---|---|---|---|---|
| redis | `redis-cli ping` (with `REDISCLI_AUTH`) | 10s | 5s | 3 | — |
| nginx | `wget -qO- http://127.0.0.1/api/v1/health` | 30s | 5s | 3 | 10s |
| backend | `urllib.request.urlopen('http://localhost:8000/api/v1/health')` | 30s | 10s | 3 | 10s |
| frontend | `wget -qO- http://127.0.0.1:3000` | 30s | 5s | 3 | — |

All services use `restart: unless-stopped`.

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

### Rate limiting and client identity

The API applies per-client rate limits (via `slowapi`). Client identity is resolved with spoof-resistance in mind:

- **Authenticated requests** are limited by the verified JWT subject (`user:<sub>`), which is stable per user and cannot be rotated by an attacker.
- **Requests behind a trusted proxy** use the rightmost *untrusted* IP from `X-Forwarded-For`. The header is only trusted when the direct peer belongs to a network listed in `TRUSTED_PROXIES` (CIDR list). Configure it to match your reverse proxy (e.g. nginx in Docker: `TRUSTED_PROXIES=["127.0.0.1","172.16.0.0/12"]`).
- **Requests without a trusted proxy** ignore `X-Forwarded-For` and fall back to the direct connection peer, logging a warning when the header chain looks suspicious.

See [Issue #112](https://github.com/Finfinder/Investment-Assistant/issues/112) for the original finding.

### Security response headers

In production (`DEBUG=false`) the backend injects the following security headers into every API response via `SecurityHeadersMiddleware` (`app/core/security_headers.py`):

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'none'` (API is not browser-rendered)
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

The nginx reverse proxy adds `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and `Strict-Transport-Security` (on the HTTPS server block) at the proxy layer, and scopes a browser-oriented `Content-Security-Policy` to the frontend `location /` so the API keeps its minimal CSP. Headers are intentionally skipped in local development to avoid breaking hot reload.

See [Issue #114](https://github.com/Finfinder/Investment-Assistant/issues/114) for the original finding.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

---

## License

This project is licensed under the [MIT License](LICENSE).

