# Investment Assistant

CFD instrument technical and fundamental analysis application. Provides market data retrieval with multi-provider fallback, technical indicators, and analysis endpoints via a REST API.

## Tech Stack

### Backend

- **Python 3.13** / FastAPI / Pydantic 2
- **SQLAlchemy 2** (async, SQLite for MVP)
- **Data providers**: yfinance (primary), Twelve Data, Financial Modeling Prep
- **Analysis**: pandas-ta, TA-Lib

### Frontend

- **Next.js 14** (App Router) / TypeScript 5
- **TailwindCSS 3.4** with CSS custom properties (dark theme)
- **lightweight-charts v5** for interactive candlestick charts
- **Docker Compose** for full-stack deployment

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

### Docker

```bash
docker compose up --build
```

Backend API: `http://localhost:8000`. Frontend: `http://localhost:3000`. Health check: `GET /api/v1/health`.

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

Detects candlestick patterns (15 types via TA-Lib), support/resistance levels with strength scoring, Fibonacci retracement levels, IKI (Impulse-Correction-Impulse) patterns, and geometric chart patterns (triangle, wedge, flag, pennant).

### Fundamental Analysis

```
POST /api/v1/fundamental-analysis
{"symbol": "EURUSD"}
```

Automatically routes to the correct analyzer based on instrument type. Forex pairs compare interest rate and inflation differentials between base and quote currencies. Commodities analyze COT positioning, USD strength, and rate environment. Indices evaluate regional macro data (rates, unemployment). Data sourced from FRED API and Financial Modeling Prep.

### Full Analysis Pipeline

```
POST /api/v1/analysis
{"symbol": "EURUSD", "timeframe": "H1"}
```

Triggers an asynchronous 6-step pipeline: data fetch → technical analysis → pattern recognition → fundamental analysis → signal aggregation → strategy generation. Returns an `analysis_id` to poll via `GET /api/v1/analysis/{id}` or subscribe via `WS /api/v1/ws/analysis/{id}` for live progress updates. The final report includes weighted signal scoring, entry point scenarios (aggressive and conservative), SL/TP levels, and confidence percentages.

## Configuration

Copy `backend/.env.example` to `backend/.env`. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `TWELVE_DATA_API_KEY` | Twelve Data API key (optional) | — |
| `FMP_API_KEY` | Financial Modeling Prep API key (optional) | — |
| `FRED_API_KEY` | FRED API key (optional) | — |
| `CACHE_TTL_INTRADAY` | Cache TTL for intraday data (seconds) | 300 |
| `CACHE_TTL_DAILY` | Cache TTL for daily data (seconds) | 3600 |

## Testing

```bash
# Backend
cd backend
python -m pytest tests/ -v

# Frontend lint & type-check
cd frontend
npm run lint
npm run build
```

## License

MIT
