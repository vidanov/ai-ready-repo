# Security policy

## Reporting a vulnerability

**This policy does not yet identify a verified private reporting contact.**
A maintainer must supply an actual private contact or confirm a private reporting
service before this section can direct reports there.

Do not open public issues containing vulnerabilities, credentials, private data,
or exploit details. Once a private channel is available, include the affected
revision, impact, reproduction, and relevant redacted output. No acknowledgement
or resolution time is promised until the maintainer establishes that process.

## Scope and maintained version

Fixes are maintained on `main`; this repository has no backport release policy.
It contains reusable audit/adoption/verification tools, an Order example, and
research fixtures. CDK and Terraform examples live under `ecosystems/`.

- Audit reads project files and reports configuration evidence.
- Adoption previews or creates new files. It does not execute project commands.
- Verification executes the target project's Makefile with the invoking user's
  permissions. Only run it for code you trust to execute in that environment.
- Mutation drills use disposable repository copies. Those copies protect working
  files from accidental edits; they do not restrict process permissions.

## Configured checks and their limits

| Check | Local configuration | Scope |
|---|---|---|
| Dependency review | `.github/workflows/security.yml` | Pull requests only; configured to fail at moderate severity or above |
| Secret scanning | `.github/workflows/security.yml` | Gitleaks job on pushes and PRs to main; checkout fetches full history |
| Python security lint rules | `pyproject.toml`, `make lint` | Source, tests, and scripts, subject to configured rule exceptions |
| Strict type checking | `make typecheck` | Both source packages; legacy scripts are not fully typed |

These are repository declarations. Successful hosted execution, scanner coverage,
required checks, and review enforcement must be verified separately. No check
proves that the repository contains no secrets or vulnerabilities.

Python dependencies are recorded in `uv.lock`; `make bootstrap` installs with
`uv sync --frozen --all-extras`. A lockfile makes dependency selection reproducible;
it does not establish that the selected dependencies are vulnerability-free.

## Verification trust

`make verify-snapshot` copies files when invoked, including any weakening that
already happened. `verify-tamperproof` is a historical alias, not a security guarantee.
`make verify-from-git TRUSTED_REF=<reviewed-commit>` selects acceptance tests and
pytest configuration from that commit. Its default `HEAD` only protects against
uncommitted test edits relative to HEAD. The verifier, chosen ref, and execution
environment must themselves be trusted.

For stronger protection, keep the verifier and its credentials outside the
candidate's write access. A separate process alone does not provide that boundary.
See [the architecture notes](docs/architecture.md) for the local implementation.

## Credentials and hosted permissions

Keep credentials out of source, fixtures, logs, and command evidence. `.env` is
ignored; `.env.example` should contain safe examples only. If a credential is
exposed, revoke or rotate it and coordinate cleanup with the affected service
owner; deleting the local file does not revoke it.

Grant only the access needed for the task. A repository token is not proof of
branch protection: review the actual branch rules, required reviewers and checks,
and bypass privileges. The committed CODEOWNERS file still contains placeholder
team names and must be configured by the repository owner before relying on it.

Token permissions, hosted settings, private reporting, and external isolation are
operational responsibilities. The audit inventory does not certify them.
