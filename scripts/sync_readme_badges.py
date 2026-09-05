#!/usr/bin/env python3
"""Keep README.md's Open Items badge in sync with docs/backlog.md.

The badge drifted stale twice in one week (fixed manually in PR #35, then
again after this script's first version) because nothing recomputed it when
docs/backlog.md gained or resolved an item. This makes it self-correcting
instead of relying on someone noticing.

Counts "### #NNN" headings in docs/backlog.md, subtracts headings whose own
line contains "resolved" (case-insensitive — items have used both
"✅ resolved" and "(RESOLVED 2026-09-01)"), and rewrites the Open Items
badge in README.md to match. A resolved-word match elsewhere in an item's
body (e.g. inside a **Gap:** paragraph) does not count — only the heading
line itself.

Usage:
    python3 scripts/sync_readme_badges.py            # fix in place
    python3 scripts/sync_readme_badges.py --check    # exit 1 if stale, no write
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BACKLOG = REPO_ROOT / "docs/backlog.md"
README = REPO_ROOT / "README.md"

HEADING_RE = re.compile(r"^### #\d+.*$", re.MULTILINE)
BADGE_RE = re.compile(
    r"\[!\[Open Items: \d+\]"
    r"\(https://img\.shields\.io/badge/open_items-\d+-purple\.svg\)\]"
    r"\(docs/backlog\.md\)"
)


def count_open_items(contributing_text: str) -> int:
    headings = HEADING_RE.findall(contributing_text)
    resolved = [h for h in headings if "resolved" in h.lower()]
    return len(headings) - len(resolved)


def badge_text(open_count: int) -> str:
    return (
        f"[![Open Items: {open_count}]"
        f"(https://img.shields.io/badge/open_items-{open_count}-purple.svg)]"
        f"(docs/backlog.md)"
    )


def main() -> int:
    check_only = "--check" in sys.argv

    open_count = count_open_items(BACKLOG.read_text())
    expected = badge_text(open_count)

    readme_text = README.read_text()
    match = BADGE_RE.search(readme_text)
    if match is None:
        print("sync_readme_badges: no Open Items badge found in README.md", file=sys.stderr)
        return 1

    if match.group(0) == expected:
        print(f"Open Items badge in sync ({open_count}).")
        return 0

    if check_only:
        print(
            f"Open Items badge stale: README has '{match.group(0)}', "
            f"docs/backlog.md currently has {open_count} open. "
            f"Run `make sync-badges` to fix.",
            file=sys.stderr,
        )
        return 1

    README.write_text(readme_text[: match.start()] + expected + readme_text[match.end() :])
    print(f"Open Items badge updated to {open_count}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
