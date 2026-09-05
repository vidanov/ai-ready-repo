#!/usr/bin/env python3
"""Behavioral done-condition for the F-004 dead-guard eval task.

Demonstrates the fixtured failure class end to end:

  1. The reference implementation passes the BEHAVIORAL check: calling
     ``apply_discount`` with a negative discount on a *positive* price raises
     ``ValueError`` (the guard is on the executed path).
  2. An otherwise-identical DEAD-GUARD variant -- validation moved into the
     ``price <= 0`` branch, which never fires for a positive-price input --
     FAILS the same behavioral check.
  3. Yet a TEXTUAL (grep) done-condition passes on the dead-guard variant,
     because the guard string is still present in the file.

A done-condition that greps cannot separate (1) from (2); the behavioral
done-condition can. That separation is the entire point of F-004.

Exit code: 0 if and only if all three claims hold.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the reference domain importable when run from this directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dead_guard_domain import apply_discount  # noqa: E402

# 1. Reference implementation must reject a negative discount behaviorally.
try:
    apply_discount(price=100.0, discount=-0.5)
except ValueError:
    reference_behavioral = True
else:
    reference_behavioral = False

# 2. Dead-guard variant: validation placed inside the price<=0 branch. The
#    string is present in the file; the guard only fires when price <= 0.
DEAD_GUARD_VARIANT = """
def apply_discount(price, discount):
    if price <= 0:
        if discount < 0:
            raise ValueError("discount cannot be negative")
        return price
    return price * (1 - discount)
"""

_variant_ns: dict = {}
exec(DEAD_GUARD_VARIANT, _variant_ns)  # noqa: S102 - fixed, local source
_variant = _variant_ns["apply_discount"]

try:
    _variant(price=100.0, discount=-0.5)
except ValueError:
    variant_behavioral = True  # guard fired -> behavioral done-condition passes
else:
    variant_behavioral = False  # guard dead -> behavioral done-condition FAILS

# 3. A textual grep for the guard string passes on BOTH implementations.
variant_source = DEAD_GUARD_VARIANT
reference_source = Path(__file__).resolve().parent.joinpath("dead_guard_domain.py").read_text()
grep_pattern = "raise ValueError"
grep_passes_on_reference = grep_pattern in reference_source
grep_passes_on_variant = grep_pattern in variant_source

# Behaviour of the eval task's own done-condition:
behavioral_correct = reference_behavioral is True
behavioral_catches_dead_guard = variant_behavioral is False
# A grep done-condition mis-certifies the dead-guard variant:
grep_is_insufficient = grep_passes_on_reference is True and grep_passes_on_variant is True

print(
    "reference (executed-path guard) behaviorally rejects negative discount: "
    f"{reference_behavioral}"
)
print(f"dead-guard variant behaviorally rejects negative discount:            {variant_behavioral}")
print(
    f"grep done-condition passes on reference: {grep_passes_on_reference}  "
    f"(insufficiency demo: {grep_is_insufficient})"
)

ok = behavioral_correct and behavioral_catches_dead_guard and grep_is_insufficient
print(
    f"RESULT: {'PASS' if ok else 'FAIL'} "
    "(F-004 done-condition is behavioral; grep is demonstrably insufficient)"
)

if not ok:
    print(
        "F-004 invariant violated. Reference must reject behaviorally, the "
        "dead-guard variant must not, and the textual grep must pass on both.",
        file=sys.stderr,
    )
sys.exit(0 if ok else 1)
