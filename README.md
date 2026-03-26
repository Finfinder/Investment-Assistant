# Investment Assistant

CFD instrument technical and fundamental analysis application. Provides market data retrieval with multi-provider fallback, technical indicators, and analysis endpoints via a REST API.

## Tech Stack

- **Python 3.13** / FastAPI / Pydantic 2
- **SQLAlchemy 2** (async, SQLite for MVP)
- **Data providers**: yfinance (primary), Twelve Data, Financial Modeling Prep
- **Analysis**: pandas-ta, TA-Lib
- **Docker Compose** for deployment

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

### Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Health check: `GET /api/v1/health`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/market-data/{symbol}` | Fetch OHLCV data for a CFD symbol |

### Market Data

```
GET /api/v1/market-data/EURUSD?timeframe=H1&period=30d
```

Supported symbols include forex pairs (EURUSD, GBPUSD, …), commodities (GOLD, SILVER, …), indices (US500, US30, …), and more. Timeframes: M15, H1, H4, D1. Period format: `{n}d`, `{n}m`, `{n}y`.

## Configuration

Copy `backend/.env.example` to `backend/.env`. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `TWELVE_DATA_API_KEY` | Twelve Data API key (optional) | — |
| `FMP_API_KEY` | Financial Modeling Prep API key (optional) | — |
| `CACHE_TTL_INTRADAY` | Cache TTL for intraday data (seconds) | 300 |
| `CACHE_TTL_DAILY` | Cache TTL for daily data (seconds) | 3600 |

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## License

MIT
