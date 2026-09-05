# ai-ready-repo

[![CI](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/vidanov/ai-ready-repo/actions/workflows/ci.yml)
[![Open Items: 27](https://img.shields.io/badge/open_items-27-purple.svg)](docs/backlog.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Fixtures: 8](https://img.shields.io/badge/fixtures-8_types-orange.svg)](docs/FIXTURES.md)
[![Ecosystems: 3](https://img.shields.io/badge/ecosystems-3_(+10_planned)-teal.svg)](docs/ECOSYSTEMS.md)

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
commands are listed in `ADOPTION.md`; generated verification fails while setup is
incomplete. See [the adoption guide](docs/adoption.md).

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
`make verify` adds unit tests, coverage, ADR validation, and badge synchronization.
Formatting and linting include `scripts/`; types cover both source packages.
`make test-toolkit` reports toolkit coverage separately from the example.

The Python example enforces these import directions:

```text
infrastructure → application → domain
```

`Order.status` is read-only through the public API; changes use `transition()`.

```bash
make drill-import-check       # Reject all forbidden example-layer edges
make drill-import-permit      # Permit all legal example-layer edges
make drill-reason-swap        # Distinguish syntax errors from boundary violations
make drill-transition-guard  # Reject an invalid state transition
make drill-verifier-isolation
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
