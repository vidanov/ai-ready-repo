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

---

*Add your observations here. Format: observation → why it matters → what we did.*
