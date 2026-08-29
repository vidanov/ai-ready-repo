---
id: ADR-PROC-001
status: accepted
scope:
  - CHANGELOG.md
  - docs/adr/ADR-PROC-001*
---

# Changelog lives at tagged releases, not per commit

## Decision

Between releases, the commit log is the changelog. `git log --oneline`
provides the ordered list of changes. No separate CHANGELOG.md entry is
maintained per commit or per PR.

At each tagged release (v1.0.0, v2.0.0, ...), a curated summary is written
to CHANGELOG.md covering what changed since the previous tag. The summary
groups changes by category (added, changed, fixed) and links to the relevant
PRs or commits.

## Reasons

- This repository is a template, not a library with version consumers.
  Nobody depends on a specific version or runs `npm update ai-ready-repo`.
  Users clone once (or use the template button) and diverge.
- A per-commit changelog duplicates the git log and drifts from it.
  Two sources of the same truth means neither is trusted.
- The commit messages are already descriptive (conventional commits with
  scope). `git log --oneline` reads as a changelog today.
- Curated release notes at tag boundaries serve the audience that matters:
  someone comparing "should I re-clone from the new template or keep my
  fork?" That question arises at releases, not at individual commits.

## Verification

Check that CHANGELOG.md exists and contains at least one release entry:

```bash
grep -q "^## " CHANGELOG.md && echo "✓ CHANGELOG has release entries"
```

Check that every git tag has a corresponding CHANGELOG section:

```bash
for tag in $(git tag --sort=-v:refname); do
  grep -q "$tag" CHANGELOG.md && echo "✓ $tag documented" || echo "✗ $tag missing from CHANGELOG"
done
```

## Firing condition

This ADR fires (proves its value) the first time someone asks "what changed
in v2?" and the answer is a curated section in CHANGELOG.md rather than
a raw `git log v1.0.0..v2.0.0`.

## Retirement

Replace this approach if:

- The repository becomes a published package with version consumers who
  need to evaluate upgrade risk. At that point, per-PR changelog entries
  (e.g. via towncrier or changesets) provide the granularity consumers need.
- The time between tagged releases exceeds 6 months and the commit log
  becomes too long to curate retrospectively.
