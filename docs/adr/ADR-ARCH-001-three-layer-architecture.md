---
id: ADR-ARCH-001
status: accepted
scope:
  - src/ai_ready_repo/**
  - pyproject.toml
---

# Three-layer architecture with enforced import boundaries

## Decision

The codebase is organised into three layers with a strict one-way import direction:

```
infrastructure  →  application  →  domain
```

- `domain` contains pure business logic. It MUST NOT import from `application` or `infrastructure`.
- `application` orchestrates domain objects into use cases. It MAY import `domain`.
- `infrastructure` implements external adapters (databases, APIs). It MAY import `domain` and `application`.

Import boundaries are enforced by `import-linter` contracts in `pyproject.toml`.

## Reasons

- Domain logic stays testable without mocking external services. Every domain
  test runs in milliseconds with no setup.
- A violation means a dependency arrow points the wrong way: infrastructure
  leaking into business rules, or application logic depending on a specific
  database. These couplings compound over time and make the domain untestable.
- Enforcement by tooling means agents and humans get the same feedback
  immediately, not in a code review days later.

## Verification

Run the import boundary check:

```
make import-check
```

Inspect the contracts directly:

```
grep -A5 "importlinter.contracts" pyproject.toml
```

Both contracts must report `KEPT`. A `BROKEN` result means a layer imported
something it should not have.

## Retirement

Remove this constraint if:

- The codebase moves to a different module structure (e.g. feature-sliced
  vertical modules) where cross-cutting imports are the intended pattern.
- The project shrinks to a single module where layering adds ceremony without
  protecting anything.

Review if `make import-check` has never caught a real violation in 6 months —
a gate that never fires may be enforcing a boundary nobody is tempted to cross.
