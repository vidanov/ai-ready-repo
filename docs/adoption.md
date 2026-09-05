# Adopting into an existing repository

Use a checkout of this repository with `make bootstrap`, or install the toolkit
from a reviewed revision. The scripts are now compatibility entry points into
`src/ai_ready`; downloading an individual script is no longer supported.

## 1. Inventory configuration

```bash
uv run ai-ready audit /path/to/project
uv run ai-ready audit /path/to/project --json
```

This reads files without executing Makefiles, invoking target-project tools, or
querying hosted settings. Configuration findings do not imply that checks work.

## 2. Preview the patch

```bash
uv run ai-ready adopt /path/to/project
# For a mixed Python/Node project:
uv run ai-ready adopt /path/to/project --stack python
```

The preview is a unified diff. Existing Makefiles and agent instructions are
preserved. Node projects retain their package scripts and npm/pnpm/Yarn lockfile
choice. CDK requires `cdk.json` plus `package.json`; a TypeScript config alone is
not CDK evidence. Conflicting lockfiles are an error.

Python projects reuse configured Ruff, mypy, pytest and import-linter commands.
A uv or Poetry lockfile determines the environment command. Missing configuration
becomes a setup gap instead of an assumed tool installation. Detection supports
additional stacks, but generation currently supports Python and Node/CDK only.

## 3. Apply and finish configuration

```bash
uv run ai-ready adopt /path/to/project --apply
```

Only new files are created. Inspect `ADOPTION.md` and resolve its remaining work.
If an existing Makefile was preserved, integrate the proposed commands manually.
Generated verification has an `adoption-incomplete` prerequisite when required
setup is missing; remove it only after configuring those checks.

No dependency installation, CI modification, branch-protection change, or
project execution happens during adoption. After review, run the bootstrap
command from inside the target project, followed by its verification command.

## 4. Record executed evidence

```bash
uv run ai-ready verify /path/to/project --json
```

This executes the target project's `make verify`, retaining its exit code,
output, duration, and directory. The target Makefile is executable code. A timeout
or failure to start produces unknown evidence and a nonzero CLI result.

## 5. Demonstrate critical constraints

Define the import directions and domain invariants specific to the project.
Document their reasons in ADRs, then create disposable drills that reject known
violations and permit legal behavior. The order example and `drill-import-*`
targets demonstrate this pattern; adoption does not copy those business rules
into unrelated projects.

Connect the verified command to CI and review enforcement settings separately.
Only comparative agent runs can establish whether the changes improve agent
success, retries, time, or cost; follow [the benchmark protocol](../benchmarks/README.md).

## Compatibility

`python3 scripts/adopt.py PATH` now previews by default; pass `--apply` to write.
`--dry-run` and `--detect` remain available. `make adopt REPO=PATH` explicitly
applies, while `make adopt-dry-run REPO=PATH` previews. Both operate additively.
`python3 scripts/ai_readiness_audit.py PATH` remains a configuration inventory.

## Agent-assisted improvement

Install the repository-owned skill into your agent's skill directory. For Codex,
run this from the toolkit checkout (the link keeps the skill tied to this checkout):

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD/skills/improve-repository" "${CODEX_HOME:-$HOME/.codex}/skills/improve-repository"
```

If that name already exists, inspect it before replacing it. Keep the checkout in
place while using the link. In a task opened on the target repository, request:

> Use $improve-repository to review this project and implement the most valuable
> improvements. Preserve its existing tools and verify the changes.

For findings only, ask for a review without edits. The skill can work without the
toolkit installed. It interprets configuration findings, integrates existing files,
and checks actual behavior; it does not automatically publish the result. The
skill's effectiveness has not yet been measured in comparative agent runs.
