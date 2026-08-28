#!/usr/bin/env python3
"""
Validate that all ADRs in docs/adr/ have required fields.

Required fields in each ADR frontmatter:
  - id: ADR-XXX-NNN
  - status: accepted | deprecated | superseded | proposed
  - scope: at least one path

Exits with code 1 if any ADR fails validation.
"""

import sys
from pathlib import Path
import re

ADR_DIR = Path(__file__).parent.parent / "docs" / "adr"
REQUIRED_FIELDS = ["id:", "status:", "scope:"]
VALID_STATUSES = {"accepted", "deprecated", "superseded", "proposed"}

errors: list[str] = []

adr_files = sorted(ADR_DIR.glob("*.md"))
if not adr_files:
    print("No ADR files found — add them to docs/adr/")
    sys.exit(0)

for path in adr_files:
    content = path.read_text()

    # Check frontmatter block exists
    if not content.startswith("---"):
        errors.append(f"{path.name}: missing frontmatter (must start with ---)")
        continue

    # Extract frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        errors.append(f"{path.name}: malformed frontmatter block")
        continue

    frontmatter = match.group(1)

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in frontmatter:
            errors.append(f"{path.name}: missing required field '{field}'")

    # Check status value
    status_match = re.search(r"^status:\s*(\S+)", frontmatter, re.MULTILINE)
    if status_match:
        status = status_match.group(1).lower()
        if status not in VALID_STATUSES:
            errors.append(
                f"{path.name}: invalid status '{status}' "
                f"(must be one of {sorted(VALID_STATUSES)})"
            )

    # Check that verification section exists
    if "## Verification" not in content and "## verification" not in content.lower():
        errors.append(
            f"{path.name}: missing '## Verification' section "
            "(add a command or search pattern that proves compliance)"
        )

    # Check that retirement section exists
    if "## Retirement" not in content and "## retirement" not in content.lower():
        errors.append(
            f"{path.name}: missing '## Retirement' section "
            "(state when this rule should be removed or reviewed)"
        )

if errors:
    print(f"ADR validation failed ({len(errors)} error(s)):\n")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)

print(f"✓ All {len(adr_files)} ADR(s) valid")
