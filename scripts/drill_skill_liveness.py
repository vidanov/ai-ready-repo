#!/usr/bin/env python3
"""
Drill: the shipped skill must not reference things that no longer exist.

SKILL.md is this project's most-copied artifact — adopters symlink the whole
directory — and it is a fixture like any other: it names companion files,
scripts and commands, and nothing checked that any of them were still there.
A skill that tells an agent to read `reference/toolkit.md` after that file is
renamed sends the agent looking for guidance it will never find, and the skill
itself is the last place anyone thinks to look.

Checked, for every skill under skills/:
  - relative paths it names resolve inside the skill directory
  - repository paths it names resolve from the repo root
  - `make <target>` invocations exist in the Makefile

The drill also convicts: it plants a dangling reference in a throwaway copy
and requires the same checker to reject it. A checker that passes everything
proves nothing, and this one runs against text that is nearly always valid.

Exit code:
  0 — every reference resolves, and the planted violation was convicted
  1 — a reference is dangling, or the planted violation went unnoticed
"""

import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# `reference/toolkit.md`, `scripts/adopt.py`, `docs/adoption.md` — a backticked
# token with a slash and an extension is a path claim.
_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,5})`")
# `make verify`, `make drill-imports`
_MAKE = re.compile(r"`make ([a-z][a-z0-9-]*)`")
# Paths that are examples of what an ADOPTER would have, not claims about us.
_NOT_OURS = re.compile(r"^(/absolute|\.\./|~/)")


def _make_targets(makefile: Path) -> set[str]:
    if not makefile.exists():
        return set()
    return set(re.findall(r"^([a-z][a-z0-9-]*):", makefile.read_text(), re.M))


def check(skill_md: Path, repo_root: Path) -> list[str]:
    """Dangling references in one skill file. Empty means every claim resolves."""
    text = skill_md.read_text()
    here = skill_md.parent
    targets = _make_targets(repo_root / "Makefile")
    problems = []

    for ref in sorted(set(_PATH.findall(text))):
        if _NOT_OURS.match(ref):
            continue
        # Relative to the skill, then to the repo: a skill may name either.
        if (here / ref).exists() or (repo_root / ref).exists():
            continue
        problems.append(f"{skill_md.name}: `{ref}` resolves to nothing")

    for target in sorted(set(_MAKE.findall(text))):
        # `make verify` is named as something an ADOPTER's repo might have;
        # only convict when this repo has a Makefile and lacks the target.
        if targets and target not in targets:
            problems.append(f"{skill_md.name}: `make {target}` is not a target here")

    return problems


def _convicts_a_planted_break() -> bool:
    """Plant a dangling reference in a copy and require the checker to catch it."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "skills"
        shutil.copytree(SKILLS_DIR, copy)
        planted = next(copy.rglob("SKILL.md"))
        planted.write_text(
            planted.read_text() + "\n\nSee `reference/a-file-that-was-deleted.md` for details.\n"
        )
        found = check(planted, REPO_ROOT)
        return any("a-file-that-was-deleted.md" in p for p in found)


def main() -> int:
    skills = sorted(SKILLS_DIR.rglob("SKILL.md"))
    if not skills:
        print("no skills found — nothing to check", file=sys.stderr)
        return 1

    problems = []
    for skill in skills:
        problems += check(skill, REPO_ROOT)

    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)

    if not _convicts_a_planted_break():
        print(
            "  ✗ the checker did NOT convict a planted dangling reference — "
            "it is not actually checking anything",
            file=sys.stderr,
        )
        return 1

    if problems:
        print(f"\n{len(problems)} dangling reference(s) in {len(skills)} skill(s)", file=sys.stderr)
        return 1

    print(
        f"✓ every reference in {len(skills)} skill(s) resolves; "
        f"a planted dangling reference was convicted"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
