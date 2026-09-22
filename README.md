# ai-ready-repo

[![CI](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml)
[![Open Items: 33](https://img.shields.io/badge/open_items-33-purple.svg)](docs/backlog.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Fixtures: 8](https://img.shields.io/badge/fixtures-8_runnable-orange.svg)](docs/FIXTURES.md)
[![Ecosystems: 1 done, 2 scaffold, 10 planned](https://img.shields.io/badge/ecosystems-1_done,_2_scaffold,_10_planned-teal.svg)](docs/ECOSYSTEMS.md)

A toolkit and reference example for making repository conventions executable.
Assess an existing project, preview an adoption patch, run its checks, and prove
that important constraints reject violations.

The working hypothesis is that clear commands and executable constraints help
coding agents complete tasks more reliably and with less rework. **The repository
does not yet contain comparative agent-performance measurements.** Passing tests
and using a Make target do not establish token savings or faster completion.

## Start here

```bash
git clone https://github.com/vidanov/ai-ready-repo.git
cd ai-ready-repo
make bootstrap
make verify

# Read-only configuration inventory; no target-project commands run
uv run ai-ready audit /path/to/project
uv run ai-ready audit /path/to/project --json

# Inspect the complete proposed patch before creating new files
uv run ai-ready adopt /path/to/project
uv run ai-ready adopt /path/to/project --apply

# Execute the target project's documented checks and retain their output
uv run ai-ready verify /path/to/project --json
```

Python and Node/TypeScript adoption reuse existing configuration. CDK is identified
by its CDK project marker and uses the project's package scripts. Mixed projects
require `--stack python` or another detected stack. Other stacks are detected but
are not yet supported by automated adoption.

Adoption is additive and deterministic. It does not overwrite existing files,
install tools, execute the target project, or invent a Jest/ESLint setup. Missing
commands are listed in the `ADOPTION.md` that adoption writes into the target
project; generated verification fails while setup is incomplete. See
[the adoption guide](docs/adoption.md).

## Improve with an agent

The reusable [improve-repository skill](skills/improve-repository/SKILL.md) guides
an agent through evidence-based review and authorized improvements using the
project's existing tools. It covers integration work that additive adoption cannot
finish automatically. See [installation and usage](docs/adoption.md#agent-assisted-improvement).

## What each result means

| Evidence | Meaning |
|---|---|
| Configured | A relevant file, command, or tool declaration was found. |
| Executed | A verification command ran; its exit code and output are recorded. |
| Demonstrated | A drill rejected a planted violation for the expected reason. |
| Unknown | The available evidence cannot establish the property. |

The audit's configuration score is retained for compatibility. It is not a
security rating or proof that a repository is agent-safe. For example, finding
CODEOWNERS does not verify required-review settings. Agent performance remains
unknown until comparable runs have been recorded.

## Repository responsibilities

```text
src/ai_ready/                 Reusable, typed toolkit: audit, adoption, CLI, verification
src/ai_ready_repo/            Small Python order example with enforced layer boundaries
tests/unit/                  Toolkit, example, and verification regression tests
scripts/                     Compatibility entry points, maintenance checks, research drills
scripts/eval_tasks/           Verification regression tasks and failure fixtures
ecosystems/                  CDK and Terraform reference scaffolds
skills/improve-repository/   Reusable agent workflow for repository improvements
benchmarks/                  Protocol for future comparative agent measurements
docs/adr/                    Decisions explaining executable constraints
docs/articles/               Articles and historical research
docs/architecture.md         Structure, compatibility, and migration rationale
docs/adoption.md             Guide to upgrading an existing repository
docs/backlog.md              Contribution ideas and their current status
docs/research/learnings.md   Historical observations and corrections
```

The toolkit cannot import the example. The example retains its existing paths
and imports while adoption code moves into the toolkit. This keeps existing
fixtures and downstream template users working during the migration.

## Checks and drills

`make verify-fast` runs formatting, linting, types, and import contracts.
`make verify` adds unit tests, coverage, ADR validation, badge synchronization,
and verification-population coverage.
Formatting and linting include `scripts/`; types cover both source packages.
`make test-toolkit` reports toolkit coverage separately from the example.

The Python example enforces these import directions:

```text
infrastructure → application → domain
```

`Order.status` is read-only through the public API; changes use `transition()`.

```bash
# Example layer boundaries and state machine
make drill-import-check        # Reject all forbidden example-layer edges
make drill-import-permit       # Permit all legal example-layer edges
make drill-reason-swap         # Distinguish syntax errors from boundary violations
make drill-transition-guard    # Reject an invalid state transition
make drill-reachability        # Reject a status write outside transition()
make drill-reachability-coupling # Prove that check is coupled to its subject

# Repository-level constraints
make drill-dead-config         # Find pyproject.toml keys nothing references
make drill-deny-catalog        # Deny catalog is locked, additive-only, patterns fire
make drill-ci-coverage         # Every verification target runs in CI
make drill-verifier-isolation  # Committed tests ignore working-tree edits

# Verification-gate integrity (from 1f916 incidents)
make drill-measurement-invalid # Treat an unrun check as distinct from a failure
make drill-coverage-floor      # Refuse a green rate over a rotting harness
make drill-required-axis       # Reject a required-but-unexercised axis
make drill-referent-liveness   # Report a drifted-away referent as STALE_OR_DRIFTED
make drill-external-witness    # Fail the freshness gate when the external record is absent
```

Mutation drills run in disposable repository copies. They preserve pre-existing
edits and do not use the user's checkout as a scratch area. These copies prevent
accidental workspace damage; they are not operating-system security sandboxes.
See [the fixture catalog](docs/FIXTURES.md) for the research drills.

## Verification trust and measurement

- `make verify-snapshot` takes a snapshot at invocation time. Earlier weakened
  tests remain weakened. `verify-tamperproof` is a compatibility alias.
- `make verify-from-git TRUSTED_REF=<reviewed-commit>` takes acceptance tests and
  pytest configuration from the selected commit, and tests the working code.
  The default `HEAD` protects only against uncommitted test edits. The calling
  verifier itself must be trusted; stronger isolation requires an external runner.
- `make eval` runs verification regression tasks. It does **not** launch an agent
  or measure the time an agent needs to solve a task. See the
  [benchmark protocol](benchmarks/README.md) before making efficiency claims.

## Further reading

- [Architecture and migration](docs/architecture.md)
- [Adopting into an existing project](docs/adoption.md)
- [Ecosystem examples and roadmap](docs/ECOSYSTEMS.md)
- [Failure catalog and research](docs/FAILURE-CATALOG.md)
- [Articles](docs/articles/README.md) and [learnings](docs/research/learnings.md)
- [Contributing](CONTRIBUTING.md) and [backlog](docs/backlog.md)
- [Security policy](SECURITY.md), [code of conduct](CODE_OF_CONDUCT.md), and [license](LICENSE)

The central principle remains: use tools to enforce the rules they can check,
and keep human and agent guidance focused on the reasoning those tools cannot provide.

### Missing verification checks

`make population-check` enumerates prerequisites of `make verify` from the
Makefile and compares them with explicit `covers` lists in evaluation tasks.
Adding a check without a mapping fails with `REFERENT_UNAUTHORED`, even when
that check is absent from `.PHONY`. A mapping is valid only when the task's
verification command reaches that target. The check runs through `make verify`
and therefore through its existing required CI job.

The scope is the literal verification prerequisite graph, not every file or
business rule in the repository. Coverage declarations (from walter on
population coverage, 1f916 #3843) establish a mapping; `make eval` executes the
tasks and, against the committed prior in `scripts/eval_tasks/known_invalid.json`,
fails when a row that was measurable goes `measurement_invalid`. None of this
proves that tests detect every defect: the checks certify that a target is
reachable and a prior is well-formed, not that the recorded facts match the
world. A unit regression adds a check without coverage, requires failure, then
adds coverage and requires recovery.
