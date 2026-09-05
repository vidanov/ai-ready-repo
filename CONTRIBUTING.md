# Contributing to ai-ready-repo

Human and agent contributions follow the same workflow. Start with the
[backlog](docs/backlog.md), or describe a concrete gap and how to verify a fix.
The backlog keeps stable item numbers and distinguishes open, partial, and resolved work.

## Before changing code

1. Read [AGENTS.md](AGENTS.md) for commands, boundaries, and completion evidence.
2. Read [the architecture notes](docs/architecture.md) to distinguish the toolkit,
   example, and research scripts. Read the relevant ADR before changing a constraint.
3. Keep the change focused on one problem. Example features and experimental
   fixtures should not become dependencies of the reusable toolkit.
4. For user-facing behavior, update [the adoption guide](docs/adoption.md) or
   [README.md](README.md). Keep historical observations in
   [the research notes](docs/research/learnings.md).

## Verify your change

Run `make verify-fast` while changing code, then `make verify` before claiming
completion. Use the specific regression tests and disposable drills relevant to
the change. `make test-toolkit` reports toolkit coverage separately.

Record commands and exit codes, changed files, and what was not verified.
Do not infer hosted CI results, security enforcement, or agent efficiency from
local tests. `make eval` runs verification checks; comparative agent runs follow
[the benchmark protocol](benchmarks/README.md).

## Pull requests

Describe the concrete problem, resulting behavior, and verification evidence.
The [PR template](.github/PULL_REQUEST_TEMPLATE.md) supplies the structure.
Reference a backlog item when applicable and update its status based on evidence.
Run `make sync-badges` after changing backlog status; `make verify` checks the count.

Changes to review-sensitive paths follow the boundaries in AGENTS.md. Passing
checks is necessary but does not replace maintainer review. Do not weaken a
check to hide a failure; update its reasoning and regression evidence when the
intended rule itself changes.

## Report an issue

Include the expected behavior, actual behavior, reproduction, and relevant output.
Do not include credentials or private data. Use [SECURITY.md](SECURITY.md) for
security reports and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for conduct concerns.

Contributions are made under the repository's [MIT license](LICENSE).
