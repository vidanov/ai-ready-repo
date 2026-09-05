#!/usr/bin/env python3
"""
Drill: find configuration keys in pyproject.toml that nothing references.

A config key that is declared, validated by the tool, tuned to a specific
value, and read by no code at all is a dead constraint. It looks like it
governs behavior. It governs nothing. Everyone who reads the config file
believes the value matters; nobody who runs the code is affected by it.

This script extracts leaf-value keys from [tool.*] sections in
pyproject.toml and searches for each key in source files, CI workflows,
Makefile, and scripts. A key found nowhere outside pyproject.toml itself
is reported as dead.

Scope: only checks [tool.*] sections (ruff, mypy, pytest, coverage,
importlinter). Build-system and project metadata are excluded.

Exit code:
  0 — no dead config keys found
  1 — dead config keys found (names printed to stderr)
"""

import re
import sys
from pathlib import Path

# ponytail: linear scan of all source files per key, fine for <200 keys
# and <100 files; replace with an inverted index if this grows

REPO_ROOT = Path(__file__).parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Directories to search for references
SEARCH_DIRS = [
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "scripts",
    REPO_ROOT / ".github",
]
SEARCH_FILES = [
    REPO_ROOT / "Makefile",
    REPO_ROOT / "AGENTS.md",
]

# Keys that are inherently tool-internal: the tool reads them, the user
# doesn't reference them in source. These are expected to be "dead" from
# our scan's perspective.
ALLOWLIST = {
    # ruff
    "target-version",
    "line-length",
    "select",
    "ignore",
    # mypy
    "python_version",
    "strict",
    "warn_return_any",
    "warn_unused_configs",
    "disallow_untyped_defs",
    "disallow_incomplete_defs",
    # pytest
    "testpaths",
    "addopts",
    "tb",
    # coverage
    "source",
    "omit",
    "fail_under",
    "show_missing",
    # importlinter
    "root_packages",
    "include_external_packages",
    "name",
    "type",
    "source_modules",
    "forbidden_modules",
    # build system
    "requires",
    "build-backend",
}


def extract_tool_keys(pyproject_path: Path) -> list[str]:
    """Extract leaf config key names from [tool.*] sections."""
    text = pyproject_path.read_text()
    keys: list[str] = []
    in_tool = False

    for line in text.splitlines():
        stripped = line.strip()

        # Track whether we're in a [tool.*] section
        if re.match(r"\[tool\.", stripped) or re.match(r"\[\[tool\.", stripped):
            in_tool = True
            continue
        elif re.match(r"\[", stripped) and not re.match(r"\[tool", stripped):
            in_tool = False
            continue

        if not in_tool:
            continue

        # Extract key from "key = value" lines
        m = re.match(r"(\w[\w-]*)\s*=", stripped)
        if m:
            keys.append(m.group(1))

    return keys


def find_references(key: str) -> list[str]:
    """Search for a key in source files, returning file paths where found."""
    found = []

    for search_dir in SEARCH_DIRS:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".py", ".yml", ".yaml", ".toml", ".md", ".sh", ""):
                continue
            try:
                if key in f.read_text():
                    found.append(str(f.relative_to(REPO_ROOT)))
            except (UnicodeDecodeError, PermissionError):
                continue

    for f in SEARCH_FILES:
        if f.exists():
            try:
                if key in f.read_text():
                    found.append(str(f.relative_to(REPO_ROOT)))
            except (UnicodeDecodeError, PermissionError):
                continue

    return found


def main() -> int:
    if not PYPROJECT.exists():
        print("No pyproject.toml found", file=sys.stderr)
        return 1

    keys = extract_tool_keys(PYPROJECT)
    unique_keys = sorted(set(keys) - ALLOWLIST)

    dead: list[str] = []
    for key in unique_keys:
        refs = find_references(key)
        if not refs:
            dead.append(key)

    if dead:
        print(f"✗ {len(dead)} dead config key(s) found in pyproject.toml:", file=sys.stderr)
        for k in dead:
            print(f"  - {k}", file=sys.stderr)
        print(
            "\nThese keys are declared in [tool.*] sections but referenced "
            "nowhere in source, scripts, CI, or Makefile.",
            file=sys.stderr,
        )
        print(
            "Either the key governs nothing (remove it) or the reference is missing (add it).",
            file=sys.stderr,
        )
        return 1

    print(f"✓ All {len(unique_keys)} tool config keys are referenced somewhere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
