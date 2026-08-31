# ai-ready-repo

[![CI](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml)
[![Fresh Clone](https://github.com/vidanov/ai-ready-repo/actions/workflows/fresh-clone.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/fresh-clone.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![Coverage 100% (example domain)](https://img.shields.io/badge/coverage-100%25_(example_domain)-brightgreen.svg)](htmlcov/index.html)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Fixtures: 8](https://img.shields.io/badge/fixtures-8_types-orange.svg)](docs/FIXTURES.md)
[![Open Items: 29](https://img.shields.io/badge/open_items-29-purple.svg)](CONTRIBUTING.md)
[![Ecosystems: 3](https://img.shields.io/badge/ecosystems-3_(+10_planned)-teal.svg)](docs/ECOSYSTEMS.md)

Make your AI coding agents faster, cheaper, and more reliable.

An agent working in a well-structured repo completes tasks in one pass instead
of three. It never wastes tokens guessing how to run tests, what the
architecture is, or which imports are allowed. Every answer is in the toolchain,
not in a prose file the model might misread.

This template is the structure. Clone it, adopt it into an existing repo, or
use it as a reference for what "AI-ready" looks like in practice.

→ Read the accompanying article: [How to Make a Repository AI-Ready](https://dev.to/aws-builders/how-to-make-a-repository-ai-ready-3j62)

---

## Why this matters (the cost argument)

| Without structure | With structure |
|---|---|
| Agent asks "how do I run tests?" — 3 retries, 3× tokens | `make verify` — one command, first try |
| Agent puts DB code in the domain layer — review rework | Import boundary rejects it before the PR opens |
| Agent weakens a test to make it pass — silent regression | `make verify-tamperproof` catches it from a trusted copy |
| Agent discovers constraints by failing — trial-and-error loops | `AGENTS.md` + visible rules — works within them on first try |
| New agent or new human — hours of tribal knowledge transfer | `make bootstrap && make verify` — productive in 60 seconds |

At $3-15 per million tokens, a repo that needs 3 agent cycles instead of 1 is
3× more expensive. The structure pays for itself on the first task.

---

## What this template gives you

**Productivity (the agent works faster):**

| Layer | What it does |
|---|---|
| **One bootstrap command** | `make bootstrap` — fresh clone to working state in seconds |
| **Task interface** | `Makefile` with named targets: `verify`, `test`, `lint`, `typecheck` — no guessing |
| **Pinned toolchain** | `.python-version`, `pyproject.toml` with locked deps — no version drift |
| **Import boundaries** | import-linter contracts — the agent knows which imports are legal without asking |
| **ADRs with retirement** | Every constraint explains why it exists and when to remove it — no fear of dead rules |
| **Tool bridges** | `make setup-tools` — one command wires AGENTS.md into Cursor, Copilot, Claude, Kiro, Aider, Gemini, Windsurf |
| **Multi-ecosystem** | Python, CDK TypeScript, Terraform — same patterns, native tools |
| **Adopt existing repos** | `python scripts/adopt.py /path/to/repo` — detects your stack, generates the scaffold |

**Safety (the agent can't break things silently):**

| Layer | What it does |
|---|---|
| **Formatter + linter + typecheck** | ruff, mypy strict — deterministic, no style debates |
| **Verification drills** | `make drill-*` — proves each gate can actually reject a violation |
| **Tamper-proof verification** | `make verify-tamperproof` — runs checks from a trusted copy |
| **Fixture catalog** | 14 known failure classes in `docs/FAILURE-CATALOG.md`, 8 implemented with drills |
| **Agent eval tasks** | `scripts/eval_tasks/` with baseline tracking and 5% regression gate |
| **CODEOWNERS** | Routes sensitive paths to reviewers |
| **Security scanning** | Dependency review + gitleaks in CI |
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
│   ├── FIXTURES.md                   Verification fixture catalog (8 implemented, 14 total).
│   └── ECOSYSTEMS.md                 Multi-ecosystem roadmap and pattern mapping.
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
├── llms.txt                          AI discovery file (llmstxt.org standard).
├── AGENTS.md                         Agent guidance (minimal, non-redundant).
├── .cursor/rules/                    Per-path scoped rules for Cursor.
├── CONTRIBUTING.md                   29 open items with acceptance tests.
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

### Run the audit on your own repo

Locally:

```bash
python3 scripts/ai_readiness_audit.py /path/to/your/repo
```

As a GitHub Action (in any repo):

```yaml
- uses: vidanov/ai-ready-repo/.github/actions/ai-readiness-audit@main
  with:
    fail-below: '10'  # optional: fail if score < 10
```

The action outputs `score` (0-20), `level` (0-4), and writes a summary to the job log.

To upgrade an **existing repository**, follow the step-by-step guide in [ADOPT.md](./ADOPT.md),
or generate a starting scaffold automatically:

```bash
python3 scripts/adopt.py /path/to/your/repo --dry-run   # preview
python3 scripts/adopt.py /path/to/your/repo             # generate Makefile, AGENTS.md, SECURITY.md, ADR template
```

The generated files are a starting point, not a trusted output — review every
line before committing. Run `make audit` first — it scores your current
repository and tells you exactly what to do next.

---

## Contributing (humans and agents welcome)

[CONTRIBUTING.md](./CONTRIBUTING.md) lists open items that any contributor — human or AI agent — can pick up and submit as a PR. The workflow is stateless: everything needed is in the repository itself.

Patterns and observations discovered while working here are collected in [LEARNINGS.md](./LEARNINGS.md). Add yours.

---

## It already happened

On August 29, 2026, an AI agent ([whitehat-explorer](https://1f916.ai/) on the
1f916.ai forum) found this repository through a community discussion, read the
fixture catalog, and submitted a pull request implementing F-004 (dead-guard
detection) — a failure class the original author had documented but not built.

The agent's operator [woke up to find the PR merged](https://dev.to/aws-builders/how-to-make-a-repository-ai-ready-3j62#comment-2p5hj):

> *"I woke up to quite a start this morning to see that 'my' pull request had
> been merged into your ai-ready-repo and I was like... what? Turns out my
> Hermes instance that I had sent off to participate on 1f916 as an experiment
> decided to author it. Weird times."*
> — Peter Hebert

This is the stranger-origin principle working as designed: an external agent,
with a different model of what varies, found a gap, implemented the fix, and
passed `make verify` — without its operator knowing. The repo's structure was
legible enough for an agent that had never seen it before to contribute on the
first try.

---

## The principle

Structure makes agents productive. Enforcement keeps them safe. The two
compound: an agent that knows the rules works within them on the first try,
which is faster and cheaper than an agent that discovers rules by breaking them.

Every rule that can be enforced by a tool should be enforced by a tool.
`AGENTS.md` documents only what the tools cannot check. The repository should
be able to determine whether a patch belongs — not the instruction file.
