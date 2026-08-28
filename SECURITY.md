# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes    |

Fixes are applied to `main` only. No backport releases.

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Email: **security@example.com** (replace with your address before publishing)

Include:
- A description of the vulnerability and its impact
- Steps to reproduce, or a proof-of-concept
- Any suggested fix (optional)

You will receive an acknowledgement within 2 business days and a status update
within 7 days. If the issue is confirmed, a fix will be coordinated before any
public disclosure.

## Automated security controls

This repository enforces the following controls on every push and pull request:

| Control | Tool | Workflow |
|---------|------|----------|
| Dependency vulnerability scan | `actions/dependency-review-action` | `.github/workflows/security.yml` |
| Secret / credential scan | `gitleaks` (full history) | `.github/workflows/security.yml` |
| Linting for security patterns | `ruff` (bandit rules) | `.github/workflows/ci.yml` |
| Static type checking | `mypy --strict` | `.github/workflows/ci.yml` |

## Secrets and credentials

- No secrets are stored in this repository.
- `.env` is listed in `.gitignore`. Use `.env.example` as a reference.
- The `secret-scan` CI job scans the full git history on every push.
- If a secret is accidentally committed, rotate it immediately, then remove it
  from history with `git filter-repo` before pushing.

## Dependency policy

- All dependencies are pinned in `uv.lock`.
- The dependency-review action blocks PRs that introduce vulnerabilities rated
  `moderate` or higher.
- Run `uv pip audit` locally to check for known vulnerabilities before opening
  a PR.

## Scope

This template repository contains example domain logic only (the `Order` state
machine). There is no production data, no authentication surface, and no
external service integrations in the default configuration. Infrastructure
code added in `src/ai_ready_repo/infrastructure/` requires `@platform-team`
review (see `CODEOWNERS`).
