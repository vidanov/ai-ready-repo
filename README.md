# ai-ready-repo

[![CI](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml)
[![Fresh Clone](https://github.com/vidanov/ai-ready-repo/actions/workflows/fresh-clone.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/fresh-clone.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![Coverage 100%](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](htmlcov/index.html)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Fixtures: 8](https://img.shields.io/badge/fixtures-8_types-orange.svg)](docs/FIXTURES.md)
[![Open Items: 17](https://img.shields.io/badge/open_items-17-purple.svg)](CONTRIBUTING.md)
[![Ecosystems: 3](https://img.shields.io/badge/ecosystems-3_(+10_planned)-teal.svg)](docs/ECOSYSTEMS.md)

A multi-ecosystem template for AI-ready repositories.

Most repositories that use coding agents add a longer `AGENTS.md` when the agent behaves poorly. This template takes the opposite approach: move the rules into executable structure so there is less to explain.

→ Read the accompanying article: [How to Make a Repository AI-Ready](https://dev.to/aws-builders/how-to-make-a-repository-ai-ready-3j62)

---

## What this template gives you

| Layer | What is included |
|---|---|
| **Pinned toolchain** | `.python-version`, `pyproject.toml` with locked dev deps |
| **One bootstrap command** | `make bootstrap` — fresh clone to working state |
| **Task interface** | `Makefile` with named targets: `verify`, `test`, `lint`, `typecheck` |
| **Formatter** | ruff format — deterministic, no style debates |
| **Linter** | ruff — security checks, import order, bug patterns |
| **Type checker** | mypy strict — converts assumptions into contracts |
| **Import boundaries** | import-linter — domain/application/infrastructure contracts enforced by CI |
| **Unit tests** | pytest with 100% coverage threshold |
| **ADR validation** | `scripts/validate_adrs.py` — every ADR must have id, status, scope, Verification, and Retirement |
| **Verification drills** | `make drill-*` — proves each gate can actually reject a violation |
| **Tamper-proof verification** | `make verify-tamperproof` — runs checks from a trusted copy agents can't weaken |
| **Fixture catalog** | 8 fixture types documented in `docs/FIXTURES.md`, community-attributed |
| **Agent eval tasks** | `scripts/eval_tasks/` with baseline tracking and 5% regression gate |
| **Daily eval workflow** | `.github/workflows/eval-daily.yml` — runs representative tasks on a schedule |
| **Fresh-clone CI** | `.github/workflows/fresh-clone.yml` — daily check that bootstrap works from zero |
| **Security scanning** | `.github/workflows/security.yml` — dependency review + gitleaks |
| **CODEOWNERS** | Routes CI, ADR, and infrastructure changes to reviewers |
| **Multi-ecosystem** | CDK TypeScript, Terraform scaffolds + 10 more planned in `docs/ECOSYSTEMS.md` |
| **AGENTS.md** | Minimal — only what cannot be inferred from running the tools |

---

## Maturity level

This template reaches **Level 2–3** from the article's maturity model:

- Level 2 (verifiable): formatter + linter + typecheck + tests + CI parity ✓
- Level 3 (agent-safe): CODEOWNERS, ADR validation, import boundaries, no production credentials ✓
- Level 4 (measured): daily eval scaffold included — wire it to your actual tasks ✓ (scaffold)

---

## Quick start

```bash
# 1. Clone or use as a template
git clone https://github.com/vidanov/ai-ready-repo.git my-project
cd my-project

# 2. Bootstrap
make bootstrap

# 3. Verify everything works
make verify
```

`make verify` runs: format-check → lint → typecheck → import-check → test-unit → validate-adrs

This is identical to what CI runs.

---

## Project structure

```
ai-ready-repo/
├── src/ai_ready_repo/                Python template (implemented)
│   ├── domain/                       Pure business logic. No external imports.
│   ├── application/                  Use cases. May import domain.
│   └── infrastructure/               External services. May import domain + application.
│
├── tests/
│   ├── unit/                         Fast, no services required.
│   └── integration/                  Requires running services.
│
├── docs/
│   ├── adr/                          Architecture Decision Records (with firing + retirement).
│   ├── articles/                     Published articles and publication index.
│   ├── FIXTURES.md                   Verification fixture catalog (7 types, attributed).
│   ├── ECOSYSTEMS.md                 Multi-ecosystem roadmap and pattern mapping.
│   └── MISSION.md                    Project vision and collaboration model.
│
├── scripts/
│   ├── eval_tasks/                   YAML task definitions for agent evaluation.
│   ├── validate_adrs.py             ADR format checker (run by CI).
│   ├── run_evals.py                 Agent evaluation runner with baseline tracking.
│   ├── verify_tamperproof.sh        Oracle-tampering protection (trusted-copy verification).
│   └── drill_transition_guard.py    Drill: proves domain guard can convict.
│
├── ecosystems/
│   ├── cdk-typescript/               AWS CDK v2, TypeScript, jest, cdk-nag (scaffold).
│   └── terraform/                    Terraform, tflint, checkov, module boundaries (scaffold).
│
├── .github/
│   ├── workflows/ci.yml             Runs on every PR.
│   ├── workflows/fresh-clone.yml    Verifies bootstrap from clean checkout (daily).
│   ├── workflows/security.yml       Dependency review + gitleaks secret scan.
│   ├── workflows/eval-daily.yml     Runs agent evals on a schedule.
│   └── CODEOWNERS                   Routes reviews to the right people.
│
├── Makefile                          Task interface: verify, drills, eval, audit.
├── AGENTS.md                         Agent guidance (minimal, non-redundant).
├── CONTRIBUTING.md                   16 open items with acceptance tests.
├── ADOPT.md                          Step-by-step adoption guide for existing repos.
└── LEARNINGS.md                      Patterns discovered while building.
```

---

## Import boundaries

The three-layer architecture is enforced by [import-linter](https://import-linter.readthedocs.io/):

```
infrastructure  →  application  →  domain
```

`domain` must not import `application` or `infrastructure`.
A violation fails CI immediately. Configuration is in `pyproject.toml` under `[tool.importlinter]`.

To check locally:

```bash
make import-check
```

---

## Architecture Decision Records

ADRs live in `docs/adr/`. Each one records a decision, its reasons, a **Verification** section (a command to confirm the constraint is still in force), and a **Retirement** section (the condition under which the rule should be removed or reviewed).

`make validate-adrs` checks that every ADR has the required fields. It runs in CI.

Template: copy `docs/adr/ADR-DOMAIN-001-order-state-machine.md` and adapt.

---

## Agent evaluations

`scripts/run_evals.py` runs representative coding tasks and measures success rate against a stored baseline. A regression of more than 5% fails the run.

To add a task, create a YAML file in `scripts/eval_tasks/`:

```yaml
description: >
  What the agent should do.

verification: "make verify"
expected_exit_code: 0
```

To set or update the baseline:

```bash
python scripts/run_evals.py --baseline
```

The daily workflow `.github/workflows/eval-daily.yml` runs this automatically. Track the results over time to see whether changes to AGENTS.md, tooling, or code structure improve or regress agent behaviour.

---

## Verification drills and fixtures

Every enforced rule needs a **firing condition**: proof that the gate can actually
reject a violation, not just that it exists in the file. A gate that has never
fired is indistinguishable from a gate that cannot fire.

The repository includes two drills:

| Drill | What it proves |
|-------|----------------|
| `make drill-transition-guard` | The `Order.transition()` guard rejects an invalid state change |
| `make drill-import-check` | The import-linter boundary gate catches a forbidden import |

Each drill plants a known violation, asserts the gate rejects it, and cleans up.
Both are linked from their respective ADR's `## Firing condition` section.

For tamper-resistant verification (prevents an agent from weakening the tests
to make them pass):

```bash
make verify-tamperproof
```

This copies verification files to a temporary directory and runs checks from
there, so an agent that modifies the Makefile or tests still fails.

The full catalog of implemented fixtures, planned fixtures, and open fixture
ideas is in [docs/FIXTURES.md](./docs/FIXTURES.md). Fixture contributions from
outside the project are especially valuable — they test failure shapes the
original author did not imagine.

---

## Ecosystems

The ai-ready pattern works across stacks. Each ecosystem in `ecosystems/`
applies the same principles (executable rules, behavioral verification, drills)
with the native tools for that stack.

| Ecosystem | Path | Stack | Status |
|-----------|------|-------|--------|
| **Python** | root (`src/`, `tests/`) | Python, uv, ruff, mypy, pytest | ✅ Complete |
| **CDK TypeScript** | `ecosystems/cdk-typescript/` | AWS CDK v2, TypeScript, jest, eslint, cdk-nag | 🟡 Scaffold |
| **Terraform** | `ecosystems/terraform/` | Terraform, tflint, checkov | 🟡 Scaffold |
| CDK Python, React, Next.js, Go, Rust, Java/Spring | planned | — | See [docs/ECOSYSTEMS.md](./docs/ECOSYSTEMS.md) |

Each ecosystem has its own `make bootstrap && make verify`. The full roadmap
and pattern mapping table are in [docs/ECOSYSTEMS.md](./docs/ECOSYSTEMS.md).

---

## Adapting this template

### Tool bridges

AGENTS.md is the single source of truth. Most tools read it natively (Codex,
Kiro, Amp, opencode, Jules, Devin, goose, Warp, RooCode, Kilo Code, Zed).
For tools that expect their own config file, generate bridge files:

```bash
make setup-tools
```

This creates:

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code (uses `@AGENTS.md` import) |
| `.cursorrules` | Cursor |
| `.windsurfrules` | Windsurf |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.aider.conf.yml` | Aider |
| `.gemini/settings.json` | Gemini CLI |

Bridges point back to AGENTS.md. Edit AGENTS.md, not the bridges.
To remove all bridges: `bash scripts/setup_tool_bridges.sh --clean`

### Replace the example domain

1. Replace the `Order` domain example with your actual domain model.
2. Update import contracts in `pyproject.toml` to match your module names.
3. Replace placeholder owners in `.github/CODEOWNERS`.
4. Add real tasks to `scripts/eval_tasks/` after your first agent session.
5. Write an ADR for every constraint you want preserved.

To upgrade an **existing repository**, follow the step-by-step guide in [ADOPT.md](./ADOPT.md).
Run `make audit` first — it scores your current repository and tells you exactly what to do next.

---

## Contributing (humans and agents welcome)

[CONTRIBUTING.md](./CONTRIBUTING.md) lists open items that any contributor — human or AI agent — can pick up and submit as a PR. The workflow is stateless: everything needed is in the repository itself.

Patterns and observations discovered while working here are collected in [LEARNINGS.md](./LEARNINGS.md). Add yours.

---

## The principle

Every rule that can be enforced by a tool should be enforced by a tool. `AGENTS.md` documents only what the tools cannot check: non-obvious behaviour, operational context, and intentional constraints that look like bugs.

The repository should be able to determine whether a patch belongs — not the instruction file.
