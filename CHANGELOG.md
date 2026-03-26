# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Data acquisition module with multi-provider fallback chain
  - yfinance provider (primary) with symbol/timeframe mapping and H4 resampling
  - Twelve Data provider (secondary) with async HTTP and rate limiting (800 req/day)
  - Financial Modeling Prep provider (tertiary) with economic calendar, COT reports, and treasury rates
  - Fallback chain manager with priority-based provider selection and timing logs
  - In-memory TTL cache for OHLCV data (intraday 300s, daily 3600s)
- Market data REST endpoint: `GET /api/v1/market-data/{symbol}`
- README and CHANGELOG documentation

## [0.1.0] - 2025-03-26

### Added

- Project foundation: FastAPI app, Pydantic settings, async SQLAlchemy with SQLite
- Domain models: 7 enums and 11 Pydantic models for OHLCV, indicators, signals
- Database layer with Alembic migrations
- Docker and Docker Compose setup
- CI pipeline with pytest, ruff, and mypy
- Health check endpoint: `GET /api/v1/health`
