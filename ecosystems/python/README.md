# Python ecosystem

Python is the primary ecosystem and lives at the repository root, not in
this subdirectory. Everything here points back there.

## Where things are

| What | Location |
|------|----------|
| Source code | [`src/ai_ready_repo/`](../../src/ai_ready_repo/) |
| Tests | [`tests/`](../../tests/) |
| Config | [`pyproject.toml`](../../pyproject.toml) |
| Makefile | [`Makefile`](../../Makefile) |
| AGENTS.md | [`AGENTS.md`](../../AGENTS.md) |
| ADRs | [`docs/adr/`](../../docs/adr/) |

## Quick start

```bash
make bootstrap   # create venv, install deps
make verify      # run all checks (same as CI)
```

## What's enforced

- **Import boundaries** — `import-linter` contracts in `pyproject.toml`
- **Type checking** — `mypy --strict`
- **Linting** — `ruff` with security rules (bandit)
- **Formatting** — `ruff format`
- **Coverage** — 80% minimum, currently 100%
- **ADR validation** — required fields and sections

## Drills

```bash
make drill-transition-guard   # domain guard fires
make drill-import-check       # boundary rejects violations
make drill-import-permit      # boundary permits legal imports
make drill-dead-config        # no dead config keys
make drill-deny-catalog       # deny rules locked and firing
make drill-ci-coverage        # verification targets in CI
```

## Why Python is at the root

The other ecosystems (`cdk-typescript/`, `terraform/`) are self-contained
subdirectories with their own `Makefile`, `AGENTS.md`, and toolchain. Python
is different because it is the template itself — the CI, the drills, the
eval runner, and the fixture catalog all run on the Python toolchain. Moving
it into a subdirectory would add indirection without adding clarity.
