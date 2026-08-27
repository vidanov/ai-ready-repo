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

### #001 — Add a `Money.subtract()` method
**Gap:** `Money` has `add()` but no `subtract()`. Callers must negate manually.
**File:** `src/ai_ready_repo/domain/__init__.py`
**Tests:** `tests/unit/test_domain_money.py` — add tests for the new method
**Rules:** Subtracting to a negative result must raise `ValueError`. Currency mismatch must raise `ValueError`. Match the existing `add()` pattern.
**Verify:** `make test-unit` passes, `make typecheck` passes

### #002 — Add a `Money.multiply(factor: Decimal)` method
**Gap:** Quantity × price calculations require a scalar multiply operation.
**File:** `src/ai_ready_repo/domain/__init__.py`
**Tests:** `tests/unit/test_domain_money.py`
**Rules:** Factor must be positive. Result rounds to 2 decimal places using `ROUND_HALF_UP`. Currency is preserved.
**Verify:** `make test-unit` passes, `make typecheck` passes

### #003 — Add a second ADR
**Gap:** Only one ADR exists. The import boundary contract (domain/application/infrastructure) is enforced by import-linter but has no ADR explaining why the layering exists.
**File:** `docs/adr/ADR-ARCH-001-three-layer-architecture.md`
**Rules:** Must follow the ADR template. Must have a `## Verification` section with the exact command to check the contract is in force.
**Verify:** `make validate-adrs` passes with 2 ADRs

### #004 — Add `conftest.py` with a shared fixture
**Gap:** There is no `conftest.py`. Integration tests will need a database fixture. Add a skeleton that future tests can use.
**File:** `tests/conftest.py`
**Content:** A `tmp_path_factory`-based fixture for a temporary SQLite database. Add a placeholder integration test that uses it.
**Verify:** `make test` passes

### #005 — Add a `make lint-changed` target
**Gap:** `make verify` runs lint on all files. Agents working on a single file pay the full cost. A `lint-changed` target should lint only files changed since the last commit.
**File:** `Makefile`
**Implementation:** `git diff --name-only HEAD | grep '\.py$' | xargs ruff check`
**Verify:** Running `make lint-changed` after touching one file only lints that file. `make verify` still lints everything.

### #006 — Write a real eval task for item #001
**Gap:** The example eval task (`scripts/eval_tasks/add-subtract-method.yaml`) describes adding `subtract()` but the method does not exist yet. After #001 is merged, this task needs to be updated so the verification command tests the actual implementation.
**Depends on:** #001
**File:** `scripts/eval_tasks/add-subtract-method.yaml`
**Verify:** `python scripts/run_evals.py` reports 1/1 passed

### #007 — Add a `pre-commit` config
**Gap:** No pre-commit hooks. Format and lint run in CI but not locally on commit. Add a `.pre-commit-config.yaml` that runs `ruff format` and `ruff check` on staged files.
**File:** `.pre-commit-config.yaml`
**Rules:** Must use pinned hook versions. Must not run tests (too slow for a commit hook). Add install instructions to `ADOPT.md`.
**Verify:** `pre-commit run --all-files` passes

### #008 — Add a `LEARNINGS.md` with patterns from the first contributions
**Gap:** Contributors (human and agent) discover things while working in this repo. Those learnings should be captured so the next contributor starts with them.
**File:** `LEARNINGS.md`
**Format:**
```markdown
# Learnings

## What we found while building this

### [Pattern name]
**Observation:** [what happened]
**Why it matters:** [consequence]
**What we did:** [fix or pattern adopted]
```
**Content:** Seed with at least two observations from building the initial scaffold.
**Verify:** `make validate-adrs` still passes (the script should not touch LEARNINGS.md)

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
