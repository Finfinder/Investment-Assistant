## Description

<!-- Describe the changes in this PR. What problem does it solve? -->

## Related Issue

<!-- Link to the related issue: Refs #123, Fixes #123, or Closes #123. For PRs targeting version branches, prefer Refs #123 unless the PR fully closes the issue on that branch. -->

## Type of Change

<!-- Check the one that applies: -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] Backend feature (new functionality in the Python/FastAPI backend)
- [ ] Frontend feature (new functionality in the Next.js frontend)
- [ ] Enhancement (improvement to existing functionality)
- [ ] Documentation (changes to docs only)
- [ ] Tests (adding or updating tests)
- [ ] CI/Infrastructure (changes to CI, Docker, nginx, or build configuration)
- [ ] Other (describe below)

## Checklist

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
- [ ] Code follows project conventions (see [`.github/copilot-instructions.md`](.github/copilot-instructions.md))
