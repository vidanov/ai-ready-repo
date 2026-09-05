# Learnings

Historical observations from building the initial scaffold, followed by current
corrections. Reviewed on 2026-09-05. These notes explain how decisions evolved;
use [the architecture notes](../architecture.md) and [ADRs](../adr/) for current rules.

---

## What we found while building the initial scaffold

### Import order matters for ruff

**Observation:** ruff's `I` rule (isort) requires stdlib imports before third-party
before local. A test file with `import pytest` before `from decimal import Decimal`
fails the lint check even though both are stdlib/third-party.

**Why it matters:** An agent that writes tests in a natural order will produce a
lint failure on the first run. The fix is immediate but the failure is surprising.

**What we did:** Pinned the import order in `pyproject.toml` and documented it
in `AGENTS.md` implicitly — `make lint-fix` fixes import ordering (`make format` only formats), so there is
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

**Historical implementation:** Added a separate `validate-adrs` CI step even
though `make verify` already ran it.

**Correction (2026-09-05):** Removed duplicate CI checks. The single `make verify`
entry point reports the failing prerequisite, and the CI-coverage checker follows
the Make dependency graph. A separate repeated check is not required for coverage.

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

**Current implementation:** The audit resolves AGENTS.md or CLAUDE.md once and
uses the same content for both checks. The specific helper changed during extraction
into `src/ai_ready/audit.py`; the consistency requirement did not.

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

---

## What we learned from community feedback (1f916 threads)

### A drill written by the guard's author tests one imagination

**Observation:** When someone other than the guard's author tries to break it,
they find failure shapes the author never considered. On our 1f916 post (#2807),
five different contributors proposed fixture types we had not imagined: dead
guards at unreachable scope, oracle tampering (agent weakens the test instead
of fixing the code), response-shape confabulation (parser based on expectation
not observation), attention topology (observing the wrong data surface), and
printer-path corruption (detector fires but result doesn't reach the consumer).

**Why it matters:** Drills prove a gate can fire. They do not prove it catches
real failures. The person who wrote the guard and the person who wrote the drill
share a mental model of what a violation looks like. Contributed fixtures from
outsiders test against a different model. This is the gap between "the gate
works" and "the gate works on things I didn't think of."

**What we did:** Created [the fixture catalog](../FIXTURES.md) and
[the failure catalog](../FAILURE-CATALOG.md). Added items #008–#012, now in
[the backlog](../backlog.md), so anyone can implement the ones we haven't built yet. The
hardest fixtures to build are the most valuable ones, because they test the
shapes the author's imagination doesn't cover.

### Silence is not evidence — a guard that has never fired is not a working guard

**Observation:** On 1f916 #2839, a citizen described a credential scrubber that
had never caught a credential on the files it was built for. Every test passed.
Investigation showed the test corpus was shaped like machine-formatted credentials,
but the real transcripts used prose-style descriptions. Same imagination, same
blind spot, mutual confirmation.

**Why it matters:** A zero on a gate does not distinguish "the rule is followed"
from "the check cannot fail." Both produce the same output: nothing. Without a
firing condition (a planted violation that proves the gate can reject), silence
and compliance are indistinguishable.

**What we did:** Added `## Firing condition` sections to both ADRs, with drills
(`make drill-transition-guard`, `make drill-import-check`) that convert silence
into evidence. The drill establishes rejection for its tested failure shape; broader coverage
and continued operation still need separate evidence.


## Toolkit extraction: what changed on 2026-09-05

- Configuration presence, executed checks, and demonstrated rejection are different
  evidence. Audit output now makes the configuration-only scope explicit.
- Public state mutation bypassed the example guard. A read-only status property
  now requires callers to use `transition()`; private Python attributes are not
  a security boundary.
- Mutation drills previously used the working checkout and destructive cleanup.
  Disposable copies now preserve pre-existing edits, including on failure.
- Reusable audit and adoption code now has its own package, type checks, and tests.
  Coverage reports include the toolkit rather than only the example.
- Make usage and self-reported attempts are not comparative agent benchmarks.
  Efficiency remains a hypothesis under the [benchmark protocol](../../benchmarks/README.md).
- Documentation needs distinct homes: root entry points, guides in docs/, backlog
  status in one file, and historical observations here. Keep current instructions
  out of retrospective incident narratives.
