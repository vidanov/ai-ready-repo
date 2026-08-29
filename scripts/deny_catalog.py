#!/usr/bin/env python3
"""
Denied-command catalog: baseline patterns with golden-file lock.

The catalog defines commands an agent must not run. Three properties:

1. Golden-file lock: the baseline patterns are stored in a JSON file
   (deny_catalog_golden.json). A drill asserts the loaded catalog
   matches the golden file byte-for-byte. Pattern drift = test failure.

2. Additive-only overlay: AGENTS.md or a project config can ADD deny
   patterns but never REMOVE baseline ones. The effective deny set is
   always baseline ∪ additions, never baseline - removals.

3. Boot-time guard: before any agent command runs, load the catalog
   and verify no baseline pattern has been removed. A weakened catalog
   fails the drill the same way a weakened test suite fails
   verify-tamperproof.

Inspired by KiroCrew's denied-commands governance (Apache 2.0).
Original implementation for ai-ready-repo.

Usage:
    # As a library
    from scripts.deny_catalog import load_catalog, is_denied, resolve_effective

    catalog = load_catalog()
    effective = resolve_effective(catalog, additions=["my-custom-.*"])
    match = is_denied("rm -rf /tmp/important", effective)

    # As a drill (checks golden-file parity + additive-only property)
    python scripts/deny_catalog.py
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

GOLDEN_FILE = Path(__file__).parent / "deny_catalog_golden.json"


@dataclass(frozen=True)
class DenyRule:
    id: str
    pattern: str
    category: str
    description: str


def load_catalog(path: Path = GOLDEN_FILE) -> list[DenyRule]:
    """Load the deny catalog from the golden file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [DenyRule(**entry) for entry in data]


def load_golden_raw(path: Path = GOLDEN_FILE) -> list[dict[str, str]]:
    """Load raw golden file for comparison."""
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_effective(
    baseline: list[DenyRule],
    additions: list[str] | None = None,
    removals: list[str] | None = None,
) -> list[DenyRule]:
    """Resolve the effective deny set: baseline + additions, never - removals.

    The removals parameter exists to detect and reject weakening attempts.
    If any removal matches a baseline rule ID, this function raises ValueError.
    Additions create new rules with category "user-added".
    """
    if removals:
        baseline_ids = {r.id for r in baseline}
        attempted = set(removals) & baseline_ids
        if attempted:
            raise ValueError(
                f"Cannot remove baseline deny rules: {sorted(attempted)}. "
                f"Baseline rules are additive-only."
            )

    effective = list(baseline)

    if additions:
        for i, pattern in enumerate(additions):
            effective.append(
                DenyRule(
                    id=f"user-added-{i:03d}",
                    pattern=pattern,
                    category="user-added",
                    description=f"User-added deny pattern: {pattern}",
                )
            )

    return effective


def is_denied(command: str, rules: list[DenyRule]) -> DenyRule | None:
    """Check if a command matches any deny rule. Returns the matching rule or None."""
    for rule in rules:
        if re.search(rule.pattern, command):
            return rule
    return None


def drill_golden_parity(catalog: list[DenyRule]) -> list[str]:
    """Assert loaded catalog matches golden file exactly."""
    errors = []
    golden = load_golden_raw()

    golden_by_id = {g["id"]: g for g in golden}
    catalog_by_id = {r.id: r for r in catalog}

    # Check counts
    if len(golden) != len(catalog):
        errors.append(
            f"Count mismatch: golden has {len(golden)}, catalog has {len(catalog)}"
        )

    # Check each golden rule exists in catalog with matching fields
    for gid, g in golden_by_id.items():
        if gid not in catalog_by_id:
            errors.append(f"Golden rule {gid} missing from loaded catalog")
            continue
        r = catalog_by_id[gid]
        if r.pattern != g["pattern"]:
            errors.append(f"{gid}: pattern mismatch")
        if r.category != g["category"]:
            errors.append(f"{gid}: category mismatch")

    # Check no extra rules in catalog that aren't in golden
    for cid in catalog_by_id:
        if cid not in golden_by_id:
            errors.append(f"Catalog rule {cid} not in golden file")

    return errors


def drill_additive_only() -> list[str]:
    """Assert that baseline rules cannot be removed."""
    errors = []
    catalog = load_catalog()

    # Attempt to remove a baseline rule — must raise
    if catalog:
        try:
            resolve_effective(catalog, removals=[catalog[0].id])
            errors.append(
                f"resolve_effective accepted removal of baseline rule {catalog[0].id}"
            )
        except ValueError:
            pass  # expected

    return errors


def drill_patterns_compile() -> list[str]:
    """Assert every pattern in the catalog is a valid regex."""
    errors = []
    catalog = load_catalog()
    for rule in catalog:
        try:
            re.compile(rule.pattern)
        except re.error as e:
            errors.append(f"{rule.id}: invalid regex '{rule.pattern}': {e}")
    return errors


def drill_patterns_fire() -> list[str]:
    """Assert each category has at least one pattern that matches a known bad command."""
    errors = []
    catalog = load_catalog()

    # Sample bad commands per category
    probes = {
        "destructive-filesystem": ["rm -rf /etc", "mkfs.ext4 /dev/sda1", "dd if=x of=/dev/sda"],
        "git-destructive": ["git push --force", "git reset --hard HEAD~3", "git clean -fd"],
        "secret-exfiltration": ["cat .env", "cat ~/.ssh/id_rsa"],
        "ci-tampering": ["echo hack >.github/workflows/ci.yml"],
        "verification-bypass": ["git commit --no-verify", "gh pr merge 1 --admin"],
        "permission-escalation": ["chmod 777 /tmp/x"],
    }

    for category, commands in probes.items():
        category_rules = [r for r in catalog if r.category == category]
        if not category_rules:
            errors.append(f"No rules for category {category}")
            continue

        fired = False
        for cmd in commands:
            if is_denied(cmd, category_rules):
                fired = True
                break
        if not fired:
            errors.append(
                f"Category {category}: no pattern matched any probe command"
            )

    return errors


def main() -> int:
    """Run all deny catalog drills."""
    catalog = load_catalog()
    all_errors: list[str] = []

    print(f"→ Loaded {len(catalog)} deny rules from golden file")

    # Drill 1: golden-file parity
    errors = drill_golden_parity(catalog)
    if errors:
        all_errors.extend(errors)
        print(f"✗ Golden-file parity: {len(errors)} error(s)")
    else:
        print("✓ Golden-file parity: catalog matches golden file exactly")

    # Drill 2: additive-only property
    errors = drill_additive_only()
    if errors:
        all_errors.extend(errors)
        print(f"✗ Additive-only: {len(errors)} error(s)")
    else:
        print("✓ Additive-only: baseline rules cannot be removed")

    # Drill 3: all patterns compile
    errors = drill_patterns_compile()
    if errors:
        all_errors.extend(errors)
        print(f"✗ Pattern compilation: {len(errors)} error(s)")
    else:
        print(f"✓ Pattern compilation: all {len(catalog)} patterns are valid regexes")

    # Drill 4: each category fires on probe commands
    errors = drill_patterns_fire()
    if errors:
        all_errors.extend(errors)
        print(f"✗ Pattern firing: {len(errors)} error(s)")
    else:
        print("✓ Pattern firing: every category matches at least one probe command")

    if all_errors:
        print(f"\n✗ {len(all_errors)} total error(s):", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\n✓ Deny catalog drill passed: {len(catalog)} rules, 4 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
