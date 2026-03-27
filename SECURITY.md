# Security Policy

## Supported Versions

Investment Assistant is currently in pre-1.0 development. Only the latest released minor version receives security updates.

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

> **Note:** This policy will be updated as the project matures toward a stable 1.0 release.

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public issues, pull requests, or discussions.**

Instead, report them privately using [GitHub Security Advisories](https://github.com/Finfinder/Investment-Assistant/security/advisories/new).

### What to Include

To help us triage and resolve the issue quickly, please include:

- **Description** of the vulnerability and its potential impact
- **Affected component** (backend API, frontend, Docker configuration, dependencies, etc.)
- **Steps to reproduce** or a proof-of-concept (if possible)
- **Affected version(s)** of Investment Assistant
- **Any suggested mitigation** or fix (optional)

### Response Timeline

| Stage | Target |
|-------|--------|
| Initial acknowledgment | Within 48 hours |
| Triage and severity assessment | Within 1 week |
| Fix development and testing | Varies by severity |
| Patch release | As soon as a fix is verified |

We will keep you informed of progress throughout the process.

## Scope

### In Scope

- Investment Assistant codebase (backend and frontend)
- Docker and nginx configuration shipped with the project
- CI/CD pipeline configuration

### Out of Scope

Please report vulnerabilities in third-party dependencies directly to their maintainers:

| Dependency | Report To |
|------------|-----------|
| yfinance | https://github.com/ranaroussi/yfinance/issues |
| FastAPI | https://github.com/fastapi/fastapi/security |
| Next.js | https://github.com/vercel/next.js/security |
| React | https://github.com/facebook/react/issues |
| TA-Lib | https://github.com/TA-Lib/ta-lib-python/issues |

If a vulnerability in a third-party dependency affects Investment Assistant specifically (e.g., an insecure default configuration we ship), that **is** in scope.

## Disclosure Policy

- We follow **coordinated disclosure**: we will work with you to understand and address the issue before any public disclosure.
- Credit will be given to the reporter in the release notes (unless you prefer to remain anonymous).
- We aim to release a fix before or simultaneously with public disclosure.

## Safe Harbor

We consider security research conducted in good faith to be authorized and will not pursue legal action against researchers who:

- Act in good faith to avoid privacy violations, destruction of data, and disruption of services
- Only interact with accounts they own or with explicit permission of the account holder
- Report vulnerabilities through the process described above
- Do not exploit a vulnerability beyond what is necessary to demonstrate the issue
