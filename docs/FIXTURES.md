# Fixtures — implemented and runnable

Mutation drills run in disposable repository copies.
Every fixture here has a documented entry point. Run it, see the result. If it
passes, the gate works. If it fails, something is miswired.

For the full catalog of known failure classes (including ideas and
research references), see [FAILURE-CATALOG.md](FAILURE-CATALOG.md).

---

## Drills

### F-001: Gate-fires drill (transition guard)

`make drill-transition-guard`

Plants an invalid transition (pending → shipped) and asserts `ValueError`
is raised. Proves the domain guard is on the executed path, not just in
the file.

### F-002: Gate-fires drill (import boundary)

`make drill-import-check`

Plants each forbidden example-layer import, asserts `lint-imports`
exits nonzero and names the specific violation, inside a disposable repository copy. Existing edits are preserved.

### F-002b: Permission drill (import boundary)

`make drill-import-permit`

Plants a legal import (application → domain) and asserts the linter
does NOT fire. A gate that rejects valid imports is as broken as one
that misses violations.

### F-003: Oracle tampering

`make verify-snapshot` (`verify-tamperproof` remains a compatibility alias).

The snapshot is taken when the command starts, so earlier test weakening is
included. This demonstrates snapshot mechanics, not tamper-proof isolation.
`make verify-from-git TRUSTED_REF=<reviewed-commit>` reads acceptance tests and
pytest configuration from that commit while exercising working implementations.
Its default `HEAD` only protects against uncommitted test edits. Both require a
trusted caller; an agent that can rewrite the verifier can defeat it.

`make drill-verifier-isolation` proves the distinction in a disposable repository:
a planted failing test affects working-tree pytest and is ignored by the committed
test run. This drill never modifies the user's tests.

### F-004: Dead-guard detection

`python scripts/run_evals.py --task dead-guard-detection`

A guard placed in an unreachable code path passes a grep but never fires.
The verifier proves the done-condition is behavioral: run the code,
observe the rejection. Contributed by whitehat-explorer (stranger origin).

### F-009: Dead constraint

`make drill-dead-config`

Scans `pyproject.toml` tool sections for config keys referenced nowhere
in source, scripts, CI, or Makefile. A config key that exists but governs
nothing is the configuration equivalent of dead code.

### F-010: Deny catalog

`make drill-deny-catalog`

20 baseline deny rules across 6 categories, golden-file locked. Checks:
golden parity, additive-only (removals rejected), pattern compilation,
and pattern firing per category.

### F-014: Monitoring coverage gap

`make drill-ci-coverage`

Verifies every verification-ladder `make` target appears in at least one
CI workflow. A check that runs locally but not in CI is enforced by
convention, not by the pipeline.

---

## Design principles

1. **Behavioral over textual.** Run the code, observe the result. Don't grep.
2. **Drill proves the gate fires. Stranger proves it catches real failures.**
3. **Silence is not evidence.** A gate that has never fired is indistinguishable
   from a gate that cannot fire.
4. **The printer is part of the system.** Test that the result survives to the consumer.
5. **Separate ran from worked.** Exit code proves the gate ran. Reason string proves it saw the violation.
6. **Test the outcome, not the command.** A guardrail that blocks a command but permits the outcome is not effective.
7. **Classify your oracle.** Native (no model), proxy (model judges), or none (unmeasured).

---

Full failure catalog with 14 fixture types, research references, and
contribution items: [FAILURE-CATALOG.md](FAILURE-CATALOG.md)
