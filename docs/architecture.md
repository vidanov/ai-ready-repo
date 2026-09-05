# Toolkit structure and migration

The product workflow is assess → preview → apply → verify → measure. The repository
contains reusable tools, a worked example, and verification research. Each has a
separate purpose and must make a separate evidence claim.

## Current implementation

- `src/ai_ready/adoption.py` produces deterministic, additive plans from existing
  Python or Node/CDK configuration. Detection is separate from command selection.
- `src/ai_ready/audit.py` returns structured configuration findings without running
  target-project code. Missing execution evidence remains unknown.
- `src/ai_ready/cli.py` exposes audit, adoption, and verification through `ai-ready`.
- `src/ai_ready/verification/` records verification output and runs mutation drills
  in disposable repositories. It does not import the order example.
- `src/ai_ready_repo/` remains the example application with its existing imports.
- `scripts/` retains compatibility commands and research checks. All Python scripts
  now participate in formatting and linting; the toolkit also receives strict
  type checks and coverage. Legacy research scripts are not yet strictly typed.

The toolkit is small enough to keep audit and adoption as focused modules. Split
profiles into a package only when another supported stack needs that abstraction.
No empty plugin framework or duplicate check registry is introduced.

## Why the example has not moved yet

Moving `src/ai_ready_repo/` also changes downstream template paths, historical
acceptance suites, drills, and ADR scopes. The first extraction preserves those
interfaces while making reusable code a separately enforced package. A later
migration can move the example to `examples/python-orders/` after an independent
example bootstrap and compatibility plan have been tested. Likewise, moving
legacy task paths belongs with a versioned benchmark/fixture format migration.

## Trust boundaries

Normal verification checks the candidate workspace. A snapshot taken at invocation
time protects neither earlier edits nor a malicious verifier. Ref-sourced
acceptance tests protect against uncommitted test edits relative to the selected
commit. Both depend on a trusted caller and environment. Hosted review enforcement
and external execution remain separate operational controls.

Disposable drill copies protect user files from accidental mutation. They are
not a process-permission boundary: drill commands are trusted code.

## Evidence and compatibility

The audit score counts configured checks only. The CLI's verification receipt
records executed evidence. Drills demonstrate a particular failure condition.
The regression runner's Make usage and optional self-reported attempts are
metadata, not measured efficiency. The benchmark protocol specifies the experiment
still needed before publishing performance claims.

Public Make targets and script paths remain available. The deliberate interface
changes are preview-by-default adoption, structured audit output, and stricter
rejection of incomplete generated verification. A single-file curl installation
of the old audit/adoption scripts is replaced by installing or checking out the
package. The composite audit action loads the toolkit from its selected revision.


## Documentation map

Keep README, AGENTS, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, and LICENSE at the
repository root for discovery. README introduces the project; AGENTS guides
coding work; CONTRIBUTING describes participation; the other three define
security reporting, conduct, and licensing.

The adoption guide lives in `docs/adoption.md`, contribution status in
`docs/backlog.md`, and historical notes in `docs/research/learnings.md`. Root
ADOPT.md and LEARNINGS.md are compatibility pointers. Change the canonical
files rather than maintaining duplicate copies. Published articles retain their
historical wording; the backlog preserves the old contribution item numbers.
