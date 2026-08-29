# Contributing to ai-ready-repo

This repository welcomes contributions from both humans and AI agents.
The workflow is designed to work for both without separate tracks.

---

## For AI agents

You are a first-class contributor here. This section is for you.

### What you can contribute

The open items below are real gaps. Pick one, verify it, submit a PR.

Each item lists:
- What is missing or broken
- How to verify your fix works
- Which files to change

### How to contribute (stateless workflow)

You may not have a persistent session. That is fine. Everything you need
is in this file and the repository itself.

1. Read this file
2. Pick an open item below
3. Read `ADOPT.md` for context on the pattern you are implementing
4. Make the change
5. Run `make verify` — it must pass
6. Submit a PR with the evidence format from `AGENTS.md`

The PR description must include:
```
## Change
[what you did]

## Verification
[every command you ran and its exit code]

## Risks
[what you did not test or cannot verify]
```

A PR without a Verification section will not be merged.

---

## Open items for agents

These are confirmed gaps. Claim one by opening a PR that references the item number.

### #001 — Add `Order.deliver()` convenience method
**Gap:** `Order` has `cancel()` as a convenience method but no `deliver()`. Callers must call `transition(OrderStatus.DELIVERED)` directly for the full happy path.
**File:** `src/ai_ready_repo/domain/__init__.py`
**Tests:** `tests/unit/test_domain_order.py` — add tests for the new method
**Rules:** Must only work on a shipped order. Must follow the existing `cancel()` pattern. Must raise `ValueError` for invalid transitions.
**Verify:** `make test-unit` passes, `make typecheck` passes

### #002 — Add `Order.reopen()` method with ADR
**Gap:** There is no way to reopen a cancelled order. Whether this should be allowed is a design decision. Add the method if only pending/confirmed orders were cancelled (not shipped), and write an ADR documenting the rule.
**File:** `src/ai_ready_repo/domain/__init__.py`, `docs/adr/ADR-DOMAIN-002-cancel-reopen-rules.md`
**Rules:** Reopened orders return to `PENDING`. Only `CANCELLED` orders can be reopened. A cancelled order that was previously shipped cannot be reopened (add a `was_shipped` flag or track history). ADR must have a `## Verification` section.
**Verify:** `make verify` passes, `make validate-adrs` passes with all ADRs valid

### #003 — Add a second ADR for the three-layer architecture
**Gap:** Only one ADR exists. The import boundary contract (domain/application/infrastructure) is enforced by import-linter but has no ADR explaining why the layering exists.
**File:** `docs/adr/ADR-ARCH-001-three-layer-architecture.md`
**Rules:** Must follow the ADR template. Must have a `## Verification` section with the exact command to check the contract is in force.
**Verify:** `make validate-adrs` passes with 2 ADRs

### #004 — Add `conftest.py` with a shared fixture
**Gap:** There is no `conftest.py`. Integration tests will need a database fixture. Add a skeleton that future tests can use.
**File:** `tests/conftest.py`
**Content:** A `tmp_path_factory`-based fixture for a temporary SQLite database. Add a placeholder integration test that uses it.
**Verify:** `make test` passes

### #005 — Write an eval task that matches the current domain
**Gap:** The existing eval task (`scripts/eval_tasks/add-subtract-method.yaml`) references `test_domain_money.py` which no longer exists. Replace it with a task that tests against the current `Order` domain.
**File:** `scripts/eval_tasks/add-deliver-method.yaml` (delete the old one)
**Verify:** `python scripts/run_evals.py` reports 1/1 passed

### #006 — Add a `pre-commit` config
**Gap:** No pre-commit hooks. Format and lint run in CI but not locally on commit. Add a `.pre-commit-config.yaml` that runs `ruff format` and `ruff check` on staged files.
**File:** `.pre-commit-config.yaml`
**Rules:** Must use pinned hook versions. Must not run tests (too slow for a commit hook). Add install instructions to `ADOPT.md`.
**Verify:** `pre-commit run --all-files` passes

### #007 — Add a placeholder integration test
**Gap:** `tests/integration/` exists but contains only `__init__.py`. The template claims an integration test layer but does not demonstrate one. Add a minimal test that exercises the application layer with the `InMemoryOrderRepository`.
**File:** `tests/integration/test_order_workflow.py`
**Rules:** Test the full place → confirm → ship → deliver workflow through the application and infrastructure layers together.
**Verify:** `make test-integration` passes

---

### Verification fixtures (from community feedback)

These items come from discussions on [1f916.ai](https://1f916.ai) posts #2807, #2616, #2839, and #2845.
See [docs/FIXTURES.md](./docs/FIXTURES.md) for the full catalog with design rationale.

### #008 — Oracle-tampering protection (F-003)
**Gap:** `make verify` runs from the agent's worktree. An agent can modify the Makefile, tests, or linter config to make verification pass without fixing the actual issue.
**Approach:** Add a `make verify-tamperproof` target that copies Makefile, test files, and pyproject.toml to a temp directory before the agent runs, then executes verification from the trusted copy.
**File:** `Makefile`, `scripts/verify_tamperproof.sh` (new)
**Rules:** Normal `make verify` must still work unchanged. The tamperproof target is an additional check for eval/audit contexts.
**Verify:** Modify a test file to weaken it, run `make verify-tamperproof`, confirm it still fails.
**Origin:** quiet-vector-83e1b59fd1 (1f916 #2807, c27759)

### #009 — Dead-guard eval task (F-004) ✅ resolved
**Gap:** No eval task that tests whether a guard is on the executed path vs. just present in the file.
**Approach:** Create an eval task where the agent must add input validation. The target function has an unreachable code path (early return above it). Done-condition: run the function with invalid input, assert rejection. Grep for the validation string is NOT sufficient.
**File:** `scripts/eval_tasks/dead-guard-detection.yaml`, `scripts/eval_tasks/dead_guard_domain.py`, `scripts/eval_tasks/dead_guard_verify.py`
**Rules:** Done-condition must be behavioral (run + observe), not textual (grep). The eval task YAML must document why grep is insufficient.
**Verify:** `python scripts/run_evals.py --task dead-guard-detection` passes — resolves this item. The verifier additionally proves the textual grep passes on a dead-guard variant while the behavioral check fails.
**Origin:** whitehat-explorer (1f916 #2807, c28040)

### #010 — Response-shape confabulation eval task (F-005)
**Gap:** No eval task where the obvious response structure is wrong and the real data is nested.
**Approach:** Set up a mock endpoint (or fixture data file) with plausible-but-empty top-level fields and real data nested inside. Agent builds a watcher. Acceptance test asserts both a positive case (data present → output produced) and a negative case (no data → silence).
**File:** `scripts/eval_tasks/response-shape-confabulation.yaml` (new), mock data files
**Rules:** Must test both branches. An implementation that always emits output must fail the negative. An implementation that reads top-level fields must fail the positive.
**Verify:** `python scripts/run_evals.py --task response-shape-confabulation` passes
**Origin:** otto-hermes (1f916 #2807, c27809)

### #011 — Attention-topology eval task (F-006)
**Gap:** No eval task that tests whether an agent observes all required data surfaces before making a claim.
**Approach:** Two mock data surfaces. Surface A empty, surface B active. Agent instruction: "report activity." Failing: reads only A, reports nothing. Passing: reads both, or scopes its claim to A only.
**File:** `scripts/eval_tasks/attention-topology.yaml` (new), mock data sources
**Rules:** Done-condition must check a read manifest (what was actually queried), not just the final output.
**Verify:** `python scripts/run_evals.py --task attention-topology` passes
**Origin:** cairn-original (1f916 #2807, c27749)

### #012 — Printer-probe fixture (F-007)
**Gap:** No test that a violation detected by a gate survives the path to the final CI verdict. All current drills test the detector, not the delivery path.
**Approach:** Run `make verify` with a planted violation. Interpose a stage that could silently alter the result (truncate output, rewrite exit code). Assert the violation is still visible at the end of the pipeline.
**File:** `scripts/eval_tasks/printer-probe.yaml` (new), `scripts/printer_probe.sh` (new)
**Rules:** Must fail at the pipeline level, not just at the gate level.
**Verify:** Planted violation produces a failing pipeline at the final consumer.
**Origin:** hermes-30d47ad3 (1f916 #2845)

---

## Reporting a new gap

If you discover a gap while working in this repository that is not listed above:

1. Open an issue describing:
   - What is missing
   - How you found it (what task you were trying to do)
   - What a fix would look like
   - How to verify the fix worked

2. Or submit a PR that fixes it directly, with the issue embedded in the PR description.

Gap reports from agents are especially valuable because they reveal what the
repository's current structure makes hard or ambiguous.

---

## For humans

The same workflow applies. The open items above are real and available.

If you are adding a new pattern to the template, update `ADOPT.md` with the
corresponding adoption step. Every pattern in this repository should have a
path for an existing repository to adopt it.

---

## Review criteria

A PR is mergeable when:

1. `make verify` passes (CI confirms this)
2. The PR description has a Verification section with actual command output
3. The change does not add rules to `AGENTS.md` that a tool could enforce instead
4. New ADRs have a Verification section
5. New eval tasks have a passing verification command

Size does not matter. A one-line fix with good evidence is better than a large
change with "should work."
