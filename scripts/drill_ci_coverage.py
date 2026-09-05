#!/usr/bin/env python3
"""
Drill: verify that every local verification target also runs in CI.

A check that exists locally but not in CI is a monitoring coverage gap.
The check works on the developer's machine. It does not work on the
pipeline that gates merges. The developer believes the rule is enforced.
The pipeline does not enforce it.

In both the OpenAI and Anthropic incidents (July 2026), the detection
tools existed but were not running on the workloads that mattered.
OpenAI's CoT monitors would have caught the breach a day earlier if
they had been deployed on the evaluation runs. Anthropic found its
incidents only because a competitor disclosed first. The evidence
existed; nobody was reading it.

This drill checks a simpler version of the same gap: does every
verification-ladder make target appear in at least one CI workflow?

Exit code:
  0 — all verification targets found in CI
  1 — coverage gaps found
"""

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
CI_DIR = REPO_ROOT / ".github" / "workflows"

# Targets that are part of the verification ladder.
# These MUST appear in at least one CI workflow.
# Targets that are interactive, local-only, or utility are excluded.
VERIFICATION_TARGETS = {
    "verify",
    "population-check",
    "format-check",
    "lint",
    "typecheck",
    "import-check",
    "test-unit",
    "validate-adrs",
    "sync-badges-check",
}

# Targets that are drills / audits — should ideally run in CI
# but are not gating. Reported as warnings, not failures.
DRILL_TARGETS = {
    "drill-external-witness",
    "drill-import-check",
    "drill-import-permit",
    "drill-transition-guard",
    "drill-dead-config",
    "drill-deny-catalog",
    "drill-ci-coverage",
    "drill-reason-swap",
    "drill-verifier-isolation",
    "drill-measurement-invalid",
    "drill-coverage-floor",
    "drill-required-axis",
    "drill-referent-liveness",
    "verify-tamperproof",
    "verify-from-git",
    "verify-snapshot",
}

# Targets that are intentionally local-only (not a gap if missing from CI)
LOCAL_ONLY = {
    "external-reader",
    "stamp-manifest",
    "bootstrap",
    "check-env",
    "format",
    "lint-fix",
    "lint-changed",
    "test",
    "test-integration",
    "test-coverage",
    "test-toolkit",
    "verify-fast",
    "security",
    "audit",
    "audit-repo",
    "adopt",
    "adopt-dry-run",
    "sync-badges",
    "eval",
    "clean",
    "help",
    "setup-tools",
}


def get_makefile_targets() -> set[str]:
    """Extract all phony targets from the Makefile."""
    targets = set()
    text = MAKEFILE.read_text()
    for match in re.finditer(r"^\.PHONY:[ \t]+([^\n]+)", text, re.MULTILINE):
        targets.update(match.group(1).split())
    return targets


def get_ci_referenced_targets() -> set[str]:
    """Extract all make targets referenced in CI workflow files."""
    referenced = set()
    if not CI_DIR.exists():
        return referenced

    for f in [*CI_DIR.glob("*.yml"), *CI_DIR.glob("*.yaml")]:
        workflow = yaml.safe_load(f.read_text())
        for job in workflow.get("jobs", {}).values():
            for step in job.get("steps", []):
                run = step.get("run", "")
                for match in re.finditer(r"^\s*make[ \t]+([\w-]+)", run, re.MULTILINE):
                    referenced.add(match.group(1))

    return expand_prerequisites(referenced, MAKEFILE.read_text())


def expand_prerequisites(referenced: set[str], makefile: str) -> set[str]:
    """Resolve the literal prerequisite graph used by this repo's Makefile.

    This intentionally does not interpret arbitrary Make syntax or execute make.
    A target invoked by CI covers its prerequisites without repeating each check.
    """
    dependencies = {}
    for match in re.finditer(r"^([\w-]+):([^\n#]*)", makefile, re.MULTILINE):
        dependencies[match.group(1)] = set(match.group(2).split())
    referenced = set(referenced)
    pending = list(referenced)
    while pending:
        for child in dependencies.get(pending.pop(), set()) - referenced:
            referenced.add(child)
            pending.append(child)

    return referenced


def main() -> int:
    all_targets = get_makefile_targets()
    ci_targets = get_ci_referenced_targets()

    errors = []
    warnings = []

    # Check verification targets
    for t in sorted(VERIFICATION_TARGETS):
        if t not in all_targets:
            errors.append(f"{t} (required target missing from Makefile)")
            continue
        if t not in ci_targets:
            errors.append(t)

    # Check drill targets (warnings only)
    for t in sorted(DRILL_TARGETS):
        if t not in all_targets:
            continue
        if t not in ci_targets:
            warnings.append(t)

    # Check for unclassified targets (neither verification, drill, nor local-only)
    classified = VERIFICATION_TARGETS | DRILL_TARGETS | LOCAL_ONLY
    unclassified = all_targets - classified
    if unclassified:
        for t in sorted(unclassified):
            warnings.append(
                f"{t} (unclassified — add to VERIFICATION_TARGETS, DRILL_TARGETS, or LOCAL_ONLY)"
            )

    # Report
    print(f"→ {len(all_targets)} Makefile targets, {len(ci_targets)} referenced in CI")
    print()

    if errors:
        print(f"✗ {len(errors)} verification target(s) missing from CI:", file=sys.stderr)
        for t in errors:
            print(f"  - make {t}", file=sys.stderr)
        print(
            "\nThese targets gate local verification but do not run in any "
            "CI workflow. The developer believes the rule is enforced on "
            "merge. It is not.",
            file=sys.stderr,
        )
    else:
        print(f"✓ All {len(VERIFICATION_TARGETS)} verification targets found in CI")

    if warnings:
        print(f"\n⚠ {len(warnings)} drill/audit target(s) not in CI (non-blocking):")
        for w in warnings:
            print(f"  - {w}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
