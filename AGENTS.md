# Agent guidance

Work in the existing project conventions. See [architecture](docs/architecture.md)
for the toolkit/example split and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution workflow.

## Commands

| Task | Command |
|---|---|
| Bootstrap | `make bootstrap` |
| Fast checks: format, lint, types, imports | `make verify-fast` |
| Full verification | `make verify` |
| Unit tests | `make test-unit` |
| Toolkit tests and coverage | `make test-toolkit` |
| Single example test | `uv run pytest tests/unit/test_domain_order.py -k test_name` |
| Format / fix lint | `make format` / `make lint-fix` |
| ADR validation | `make validate-adrs` |

## Work order

1. Read the relevant ADR before changing an import boundary, `transition()`, or
   anything under `docs/adr/`. The reasons are not recoverable from lint output.
2. Run `make verify-fast` while changing code; run `make verify` before completion
   and before committing. Add focused tests or drills for changed behavior.
3. Report the completion evidence below.

The commands enforce checks when run. They do not enforce whether an agent read
an ADR, followed this order, obtained review, or reported its work accurately.
The efficiency benefit of this order remains a hypothesis; see
[backlog #032](docs/backlog.md) and [the benchmark protocol](benchmarks/README.md).

## Architecture and constraints

- `src/ai_ready/`: reusable audit, adoption, CLI, and verification tooling.
  It must not import the example package.
- `src/ai_ready_repo/`: reference example with import direction
  `infrastructure → application → domain`. Standard-library imports are allowed
  in domain code; framework and infrastructure dependencies do not belong there.
- Formatting and linting cover source, tests, and Python scripts. Strict types
  cover both source packages; legacy scripts are not yet fully typed.
- Do not weaken import contracts to make violations pass. See
  [ADR-ARCH-001](docs/adr/ADR-ARCH-001-three-layer-architecture.md).
- Change Order status through `transition()`, never by assigning `status` or
  `_status` from a caller. See [ADR-DOMAIN-001](docs/adr/ADR-DOMAIN-001-order-state-machine.md).
- Run mutation drills through their documented entry points so they operate in
  disposable repositories and preserve existing edits.

## Boundaries — ask before modifying

- `docs/adr/`: read the relevant decision before changing constrained code.
- `.github/workflows/`: platform review required.
- `src/ai_ready_repo/infrastructure/`: platform review required.

Existing task authorization still applies. CODEOWNERS contains placeholder teams;
its presence does not demonstrate that hosted review requirements are configured.

## Completion evidence

Before claiming completion:

1. Run `make verify` and confirm it passes.
2. Report every command run and its exit code.
3. List changed files.
4. State anything that could not be verified locally.
