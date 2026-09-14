#!/usr/bin/env python3
"""Keep README.md's status badges in sync with the docs they summarize.

Three badges drifted stale because nothing recomputed them when the underlying
docs changed:
  - Open Items  <- docs/backlog.md      (drifted twice in one week; PR #35)
  - Fixtures    <- docs/FIXTURES.md      (said 8, hand-maintained)
  - Ecosystems  <- docs/ECOSYSTEMS.md    (README/llms.txt disagreed: 3 vs 12 vs 13)

This makes all three self-correcting instead of relying on someone noticing.

Counting rules:
  - Open Items: "### #NNN" headings in docs/backlog.md minus those whose own
    heading line contains "resolved" (case-insensitive).
  - Fixtures: "### F-..." headings in docs/FIXTURES.md (the runnable fixtures).
  - Ecosystems: "| **Name** |" rows under the Implemented, In progress, and
    Planned tables in docs/ECOSYSTEMS.md, reported as "done/scaffold/planned".

Usage:
    python3 scripts/sync_readme_badges.py            # fix in place
    python3 scripts/sync_readme_badges.py --check    # exit 1 if stale, no write
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BACKLOG = REPO_ROOT / "docs/backlog.md"
FIXTURES = REPO_ROOT / "docs/FIXTURES.md"
ECOSYSTEMS = REPO_ROOT / "docs/ECOSYSTEMS.md"
README = REPO_ROOT / "README.md"

HEADING_RE = re.compile(r"^### #\d+.*$", re.MULTILINE)
FIXTURE_RE = re.compile(r"^### F-\d+", re.MULTILINE)
OPEN_ITEMS_BADGE_RE = re.compile(
    r"\[!\[Open Items: \d+\]"
    r"\(https://img\.shields\.io/badge/open_items-\d+-purple\.svg\)\]"
    r"\(docs/backlog\.md\)"
)
FIXTURES_BADGE_RE = re.compile(
    r"\[!\[Fixtures: \d+\]"
    r"\(https://img\.shields\.io/badge/fixtures-[0-9A-Za-z_%()+.,-]+-orange\.svg\)\]"
    r"\(docs/FIXTURES\.md\)"
)
ECOSYSTEMS_BADGE_RE = re.compile(
    r"\[!\[Ecosystems: [^\]]+\]"
    r"\(https://img\.shields\.io/badge/ecosystems-[0-9A-Za-z_%()+.,-]+-teal\.svg\)\]"
    r"\(docs/ECOSYSTEMS\.md\)"
)


def count_open_items(text: str) -> int:
    headings = HEADING_RE.findall(text)
    resolved = [h for h in headings if "resolved" in h.lower()]
    return len(headings) - len(resolved)


def count_fixtures(text: str) -> int:
    return len(FIXTURE_RE.findall(text))


def count_ecosystems(text: str) -> tuple[int, int, int]:
    """Return (done, scaffold, planned) from the three ECOSYSTEMS.md tables."""

    def rows_between(start_header: str, end_header: str | None) -> int:
        start = text.find(start_header)
        if start == -1:
            return 0
        body_start = start + len(start_header)
        end = text.find(end_header, body_start) if end_header else len(text)
        if end == -1:
            end = len(text)
        section = text[body_start:end]
        return len(re.findall(r"^\|\s*\*\*[^*]+\*\*\s*\|", section, re.MULTILINE))

    done = rows_between("### Implemented", "### In progress")
    scaffold = rows_between("### In progress", "### Planned")
    planned = rows_between("### Planned", "\n## ")
    return done, scaffold, planned


def open_items_badge(n: int) -> str:
    return (
        f"[![Open Items: {n}]"
        f"(https://img.shields.io/badge/open_items-{n}-purple.svg)]"
        f"(docs/backlog.md)"
    )


def fixtures_badge(n: int) -> str:
    return (
        f"[![Fixtures: {n}]"
        f"(https://img.shields.io/badge/fixtures-{n}_runnable-orange.svg)]"
        f"(docs/FIXTURES.md)"
    )


def ecosystems_badge(done: int, scaffold: int, planned: int) -> str:
    label = f"{done}_done,_{scaffold}_scaffold,_{planned}_planned"
    return (
        f"[![Ecosystems: {done} done, {scaffold} scaffold, {planned} planned]"
        f"(https://img.shields.io/badge/ecosystems-{label}-teal.svg)]"
        f"(docs/ECOSYSTEMS.md)"
    )


def main() -> int:
    check_only = "--check" in sys.argv

    open_count = count_open_items(BACKLOG.read_text())
    fixture_count = count_fixtures(FIXTURES.read_text())
    done, scaffold, planned = count_ecosystems(ECOSYSTEMS.read_text())

    checks = [
        (OPEN_ITEMS_BADGE_RE, open_items_badge(open_count), "Open Items", str(open_count)),
        (FIXTURES_BADGE_RE, fixtures_badge(fixture_count), "Fixtures", str(fixture_count)),
        (
            ECOSYSTEMS_BADGE_RE,
            ecosystems_badge(done, scaffold, planned),
            "Ecosystems",
            f"{done} done / {scaffold} scaffold / {planned} planned",
        ),
    ]

    readme_text = README.read_text()
    stale = False

    for badge_re, expected, name, value in checks:
        match = badge_re.search(readme_text)
        if match is None:
            print(f"sync_readme_badges: no {name} badge found in README.md", file=sys.stderr)
            return 1
        if match.group(0) == expected:
            print(f"{name} badge in sync ({value}).")
            continue
        if check_only:
            print(
                f"{name} badge stale: README has '{match.group(0)}', "
                f"docs currently show {value}. Run `make sync-badges` to fix.",
                file=sys.stderr,
            )
            stale = True
            continue
        readme_text = readme_text[: match.start()] + expected + readme_text[match.end() :]
        print(f"{name} badge updated to {value}.")

    if check_only:
        return 1 if stale else 0

    README.write_text(readme_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
