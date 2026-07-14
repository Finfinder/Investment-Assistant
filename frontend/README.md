# Investment Assistant — Frontend

Frontend for the Investment Assistant application — technical and fundamental analysis of CFD instruments. Built with Next.js 14 (App Router), TypeScript, Tailwind CSS, and lightweight-charts.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Docker](#docker)
- [NPM Scripts](#npm-scripts)
- [Conventions](#conventions)

## Tech Stack

- **Next.js 14.2** (App Router, React 18, standalone output)
- **TypeScript 5** (strict mode)
- **Tailwind CSS 3.4** with CSS custom properties (dark theme)
- **lightweight-charts v5** — interactive candlestick charts
- **Vitest 4** — unit tests
- **Playwright** — E2E and accessibility tests

## Prerequisites

- Node.js 20+
- npm 10+
- Running Investment Assistant backend (defaults to `http://localhost:8000`)

## Local Development

```bash
npm install
npm run dev
```

Application available at `http://localhost:3000`.

## Configuration

Environment variables (optional — defaults are provided):

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend REST API URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api/v1` | Backend WebSocket URL |

Example `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1
```

## Project Structure

```
src/
├── app/                    # Next.js App Router (layout, page)
├── components/             # UI components
│   ├── AnalysisForm.tsx    # Instrument and timeframe selection form
│   ├── Chart/              # Candlestick chart (lightweight-charts)
│   ├── Fundamental/        # Fundamental analysis panel
│   ├── IndicatorTable/     # Indicator tables (oscillators, MA)
│   ├── Patterns/           # Price pattern list
│   ├── PivotPoints/        # Pivot Points
│   ├── SignalSummary/      # Signal summary
│   ├── Strategy/           # Strategy table
│   ├── Section.tsx         # Section container
│   └── ProgressIndicator.tsx
├── lib/                    # API client, formatting, signals logic
│   ├── api.ts              # HTTP/WS client (triggerAnalysis, getAnalysis)
│   ├── format.ts           # Value formatting
│   └── signals.ts          # Signal mapping
└── types/                  # TypeScript types (mirroring backend Pydantic)
    └── index.ts
```

## Testing

```bash
# Unit tests (Vitest)
npm run test

# E2E tests (Playwright)
npm run test:e2e
```

Unit tests are in `__tests__/`, E2E tests in `e2e/`.

## Docker

Production image based on `node:${NODE_VERSION}-alpine@sha256:...` (default `NODE_VERSION=20`) with Next.js standalone output. The base image is pinned by its `@sha256` digest (build argument `NODE_IMAGE_DIGEST`, default value in `frontend/Dockerfile`) to guard against supply-chain attacks and ensure reproducible builds (IA-163 / [#220](https://github.com/Finfinder/Investment-Assistant/issues/220)). The Node version is controlled by the `NODE_VERSION` build argument, which in CI is read from `frontend/.nvmrc` (the single source of truth for the frontend Node version) so the runtime image stays consistent with the pipelines. Locally you can override it, e.g. `NODE_VERSION=$(cat frontend/.nvmrc) docker compose build frontend`. The Dockerfile uses BuildKit features (e.g. `RUN --mount=type=cache`), so a BuildKit-enabled builder is required — this is the default for Docker 23.0+ (`docker build` uses BuildKit automatically). On older Docker set `DOCKER_BUILDKIT=1` or use `docker buildx build`.

> **Rotating the base image digest:** when `frontend/.nvmrc` changes or `node:${NODE_VERSION}-alpine` is rebuilt upstream, resolve the new index digest and update the default `NODE_IMAGE_DIGEST` in `frontend/Dockerfile`:
>
> ```bash
> docker buildx imagetools inspect node:$(cat frontend/.nvmrc)-alpine
> # use the value from the "Digest:" line (manifest list / index digest)
> ```
>
> The `@sha256` digest is authoritative (content-addressed): Docker resolves the digest before the tag, so the tag `node:${NODE_VERSION}-alpine` is only a human-readable hint. If you bump `.nvmrc` without updating the digest, the build does **not** fail — it silently keeps using the Node version pinned by the digest. Always rotate the digest together with `.nvmrc` to avoid a stale base image.

```bash
docker build \
  --build-arg NODE_VERSION=$(cat .nvmrc) \
  --build-arg NEXT_PUBLIC_API_URL=http://backend:8000/api/v1 \
  --build-arg NEXT_PUBLIC_WS_URL=ws://backend:8000/api/v1 \
  -t investment-assistant-frontend .
```

Port: `3000`.

## NPM Scripts

| Script | Description |
|--------|-------------|
| `dev` | Development server (`next dev`) |
| `build` | Production build (`next build`) |
| `start` | Run production build (`next start`) |
| `lint` | ESLint (`next lint`) |
| `test` | Unit tests (`vitest run`) |
| `test:e2e` | E2E tests (`playwright test`) |

## Conventions

- **Code style**: ESLint (`next/core-web-vitals`, `prettier`) + Prettier (double quotes, trailing commas, 120 print width)
- **TypeScript**: strict mode, path alias `@/*` → `./src/*`
- **Components**: functional with hooks, `"use client"` where state/effects are needed
- **Styling**: Tailwind CSS with custom properties (dark theme)
- **Charts**: dynamic import of `lightweight-charts` with `ssr: false`
- **UI language**: Polish
