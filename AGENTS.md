# AGENTS.md

This file documents what a coding agent needs to work in this repository.
It is intentionally short. If a rule can be enforced by a tool, it is not here.

## Commands

| Task | Command |
|---|---|
| Bootstrap fresh environment | `make bootstrap` |
| Full verification (same as CI) | `make verify` |
| Fast check (no tests) | `make verify-fast` |
| Unit tests only | `make test-unit` |
| Single test | `pytest tests/unit/test_domain_money.py -k test_name` |
| Format | `make format` |
| Lint + fix | `make lint-fix` |
| Type check | `make typecheck` |
| Import boundaries | `make import-check` |
| Validate ADRs | `make validate-adrs` |

## Architecture

Three layers. Import direction is one-way downward:

```
infrastructure  →  application  →  domain
```

- `domain` — pure business logic, no external imports. `Money` lives here.
- `application` — use cases that orchestrate domain objects.
- `infrastructure` — databases, APIs, external services.

Import violations fail CI (`make import-check`). Do not patch the linter config to make a violation pass.

## Boundaries — ask before modifying

- `docs/adr/` — ADRs record why constraints exist. Read the relevant ADR before changing constrained code.
- `.github/workflows/` — CI changes need platform review.
- `src/ai_ready_repo/infrastructure/` — platform review required.

## Completion evidence

Before claiming a task is complete:

1. Run `make verify` and confirm it passes.
2. Report every command run and its exit code.
3. List files changed.
4. State anything that could not be verified locally.

## Non-obvious constraints

`Money` uses `Decimal`, not `float`. See ADR-DOMAIN-001.
This is intentional — do not simplify it to float or int.
