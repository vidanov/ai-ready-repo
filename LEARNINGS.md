# Learnings

Patterns and observations discovered while building and adopting this repository.
Updated by contributors — human and agent — as they work here.

---

## What we found while building the initial scaffold

### Import order matters for ruff

**Observation:** ruff's `I` rule (isort) requires stdlib imports before third-party
before local. A test file with `import pytest` before `from decimal import Decimal`
fails the lint check even though both are stdlib/third-party.

**Why it matters:** An agent that writes tests in a natural order will produce a
lint failure on the first run. The fix is immediate but the failure is surprising.

**What we did:** Pinned the import order in `pyproject.toml` and documented it
in `AGENTS.md` implicitly — `make format` fixes it automatically, so there is
nothing to explain.

### `pytest.raises(Exception)` triggers B017

**Observation:** Catching `Exception` in `pytest.raises()` is flagged by ruff's
`B017` rule ("Do not assert blind exception"). The test must name the specific
exception type.

**Why it matters:** An agent writing a test for immutability (`frozen=True` on a
dataclass) naturally writes `pytest.raises(Exception)` — the right fix is
`pytest.raises(AttributeError)`.

**What we did:** Used `pytest.raises(AttributeError)` in the immutability test.
This is also more correct: it tests the specific failure mode, not just "something broke."

### ADR validation must be in CI, not just in the Makefile

**Observation:** During the build, `make validate-adrs` was added to `make verify`
but not initially to the CI workflow step list. The CI ran `make verify` which
called `validate-adrs`, so it worked — but the CI YAML did not have a named step
for it, making it invisible in the GitHub Actions UI.

**Why it matters:** A named CI step makes failures visible by name ("Validate ADRs
failed") rather than as an unnamed sub-failure inside "Verify."

**What we did:** Added a separate `validate-adrs` step in `ci.yml` in addition to
it being part of `make verify`. Both run, which is slightly redundant but makes
failures easy to identify.

### Coverage thresholds must be wired into the verify target

**Observation:** `fail_under = 80` was configured in `pyproject.toml` under
`[tool.coverage.report]`, but `make test-unit` ran pytest without `--cov`.
The threshold was decoration — coverage was 63% and no one noticed.

**Why it matters:** A configured-but-unenforced rule is worse than no rule. It
creates false confidence. An agent or human checks "coverage threshold: yes" and
moves on.

**What we did:** Added `--cov=src --cov-report=term-missing --cov-report=html`
to the `test-unit` target. The threshold now fails the build.

### Audit checks must use the same logic for related items

**Observation:** The AI-readiness audit accepted both `AGENTS.md` and `CLAUDE.md`
for the presence check, but hardcoded only `AGENTS.md` for the line-count check.
A Claude-only repo passed presence and failed line-count with no way to fix it.

**Why it matters:** When two checks reference the same concept (instruction file),
they must resolve the file once and share the result. Split logic drifts.

**What we did:** Resolved the instruction file once with `next()` and used it for
both checks.

### CONTRIBUTING.md open items must match the actual domain model

**Observation:** After refactoring the domain from `Money` to `Order`, eight
contribution items still referenced `Money.subtract()`, `Money.multiply()`, and
`test_domain_money.py`. The eval task pointed at a test file that no longer existed.

**Why it matters:** Stale contribution items are the worst kind of template drift.
A contributor (especially an agent) follows the instructions precisely and hits a
wall immediately. Trust in the repository drops.

**What we did:** Rewrote all open items to reference the `Order` domain. Replaced
the eval task with one that tests against the current codebase.

---

*Add your observations here. Format: observation → why it matters → what we did.*
