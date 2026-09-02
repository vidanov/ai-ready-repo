# AGENTS.md

This file documents what a coding agent needs to work in this repository.
It is intentionally short. If a rule can be enforced by a tool, it is not here.

## Commands

| Task | Command |
|---|---|
| Bootstrap fresh environment | `make bootstrap` |
| Full verification (same as CI) | `make verify` |
| Fast check (no tests: format, lint, types, imports) | `make verify-fast` |
| Unit tests only | `make test-unit` |
| Single test | `pytest tests/unit/test_domain_order.py -k test_name` |
| Format | `make format` |
| Lint + fix | `make lint-fix` |
| Type check | `make typecheck` |
| Import boundaries | `make import-check` |
| Validate ADRs | `make validate-adrs` |

## Work order

Climb only as far as you need. The cheap checks falsify a wrong step in
under a second; the slow ones only earn their cost once the cheap ones pass.

1. **Before you edit constrained code, read its ADR.** This is the one step no
   tool can enforce — a linter cannot tell whether you read the reasoning. If
   you are about to touch an import boundary, `transition()`, or anything under
   `docs/adr/`, read the ADR first. Skipping this is how an agent discovers a
   constraint by violating it, then spends cycles undoing the violation.
2. **While editing, run `make verify-fast`** (format, lint, types, imports —
   ~0.5s). It catches a wrong architectural decision immediately, before you
   build on it.
3. **Before committing, run `make verify`** once, when verify-fast is green. It
   adds tests, coverage and ADR validation.
4. **To claim done, follow Completion evidence below.**

Everything in steps 2–4 is enforced by the tools named. Step 1 is the only
rule that depends on you. That is why it is the only one written here — the
rest the Makefile makes true whether you read this or not.

Note: this ordering is a hypothesis about efficiency, not a proven result. See
CONTRIBUTING.md #032 — it is not yet measured against `attempts_to_green`.

## Architecture

Three layers. Import direction is one-way downward:

```
infrastructure  →  application  →  domain
```

- `domain` — pure business logic, no external imports. `Order` lives here.
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

`Order` status changes must go through `transition()`, never direct assignment. See ADR-DOMAIN-001.
This is intentional — do not bypass the state machine.
