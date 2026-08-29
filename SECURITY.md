# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes    |

Fixes are applied to `main` only. No backport releases.

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Email: **security@example.com** (replace with your address before publishing)

Include:
- A description of the vulnerability and its impact
- Steps to reproduce, or a proof-of-concept
- Any suggested fix (optional)

You will receive an acknowledgement within 2 business days and a status update
within 7 days. If the issue is confirmed, a fix will be coordinated before any
public disclosure.

## Automated security controls

This repository enforces the following controls on every push and pull request:

| Control | Tool | Workflow |
|---------|------|----------|
| Dependency vulnerability scan | `actions/dependency-review-action` | `.github/workflows/security.yml` |
| Secret / credential scan | `gitleaks` (full history) | `.github/workflows/security.yml` |
| Linting for security patterns | `ruff` (bandit rules) | `.github/workflows/ci.yml` |
| Static type checking | `mypy --strict` | `.github/workflows/ci.yml` |

## Secrets and credentials

- No secrets are stored in this repository.
- `.env` is listed in `.gitignore`. Use `.env.example` as a reference.
- The `secret-scan` CI job scans the full git history on every push.
- If a secret is accidentally committed, rotate it immediately, then remove it
  from history with `git filter-repo` before pushing.

## Dependency policy

- All dependencies are pinned in `uv.lock`.
- The dependency-review action blocks PRs that introduce vulnerabilities rated
  `moderate` or higher.
- Run `uv pip audit` locally to check for known vulnerabilities before opening
  a PR.

## Scope

This template repository contains example domain logic only (the `Order` state
machine). There is no production data, no authentication surface, and no
external service integrations in the default configuration. Infrastructure
code added in `src/ai_ready_repo/infrastructure/` requires `@platform-team`
review (see `CODEOWNERS`).

## Agent token scope

When granting an AI coding agent access to this repository, use a GitHub
fine-grained personal access token with minimum permissions. The token scope
is the credential boundary that determines what the agent can do regardless
of how creative it is.

**Recommended permissions:**

| Permission | Level | Why |
|------------|-------|-----|
| `contents` | Write | Create branches, push commits |
| `pull-requests` | Write | Open and update pull requests |
| `metadata` | Read | Required for all fine-grained tokens |

**Permissions to withhold:**

| Permission | Why |
|------------|-----|
| `administration` | Allows `gh pr merge --admin`, bypassing required reviews |
| `bypass branch protections` | Nullifies branch protection rules entirely |

With this configuration the agent can create branches, push code, and open
pull requests. It cannot merge past required reviews, delete branches it does
not own, or modify repository settings. The creative workaround path (branch,
PR, self-merge) dies at the merge step because the token cannot satisfy the
review requirement and cannot bypass it.

This is the same principle as Unix file permissions: the process runs as a
user with limited rights. It does not matter how creative the process is.
The kernel enforces the boundary, not the process's instructions.

**Both layers required.** Token scope and branch protection work together.
A correctly scoped token on an unprotected branch still allows direct merge.
Branch protection on a repository where the agent holds an admin token still
allows `gh pr merge --admin`. Drop either layer and the agent finds the gap.

### Alternative: zero-token model

A stricter approach gives the agent no GitHub token at all. The agent works
on files locally. All Git operations (commit, push, PR creation) flow through
a separate process that holds the write credential and applies it only to
deterministic operations the agent cannot influence.

In this model:
- The agent's shell has no `GITHUB_TOKEN`, `GH_TOKEN`, or stored `gh auth`
  session. `git push` and `gh` commands fail with authentication errors.
- A post-step hook diffs the worktree, commits changes, and pushes using
  a credential the agent never sees.
- PR comments and status updates go through engine-owned reporters, not
  agent-initiated commands.

The security property is enforced by absence, not by filtering. An agent
that is prompt-injected into attempting `gh secret set` or `git push --force`
has nothing to authenticate with. No denylist to bypass, no scope to escalate.

This model requires more infrastructure (a trusted committer process, mediated
read access for `gh` queries) and is appropriate for environments where the
agent processes untrusted input (issue bodies, PR descriptions, fetched web
pages) that could carry prompt-injection payloads.

The scoped-token model above is simpler and sufficient for trusted single-user
workflows where the operator controls all inputs.
