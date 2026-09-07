#!/usr/bin/env python3
"""Behavioral done-condition for the F-004 dead-guard eval task (discount example).

This is now a THIN caller. The universal F-004 proof procedure lives in
scripts/falsifiers/dead_guard.py; this file only fills that runner's slots with
one concrete surface -- apply_discount -- and reports the result. The split is
the first step from a single-repo failure catalog toward a portable falsifier
registry: the discount example is one filled slot-set, and another surface
(e.g. a live route table) would be a different slot-set of the SAME runner.

The three claims, unchanged from before:
  1. Reference apply_discount rejects a negative discount behaviorally.
  2. A dead-guard variant (validation inside the price<=0 branch) does NOT.
  3. A textual grep for the guard string passes on BOTH.

Exit 0 iff all three hold.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the reference domain and the generic runner importable.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "falsifiers"))

import dead_guard as f004  # noqa: E402  (scripts/falsifiers/dead_guard.py)
from dead_guard_domain import apply_discount  # noqa: E402

# ── Fill the F-004 slots for the discount surface ────────────────────────────

# The dead-guard variant: validation placed inside the price<=0 branch, so the
# guard only fires when price <= 0 and is dead for the positive-price probe.
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
_dead_variant_fn = _variant_ns["apply_discount"]

PROBE_INPUT = {"price": 100.0, "discount": -0.5}  # MUST take the executed path
GUARD_PATTERN = "raise ValueError"
REFERENCE_SOURCE = (_HERE / "dead_guard_domain.py").read_text()

result = f004.run(
    reference_fn=apply_discount,
    dead_variant_fn=_dead_variant_fn,
    probe_input=PROBE_INPUT,
    guard_pattern=GUARD_PATTERN,
    reference_source=REFERENCE_SOURCE,
    variant_source=DEAD_GUARD_VARIANT,
)

# ── Report (output shape preserved for the eval task's expected_reason) ───────

print(
    "reference (executed-path guard) behaviorally rejects negative discount: "
    f"{result.reference_fires}"
)
print(
    "dead-guard variant behaviorally rejects negative discount:            "
    f"{not result.variant_is_dead}"
)
print(
    f"grep done-condition passes on reference: True  "
    f"(insufficiency demo: {result.grep_matches_both})"
)
print(
    f"RESULT: {'PASS' if result.ok else 'FAIL'} "
    "(F-004 done-condition is behavioral; grep is demonstrably insufficient)"
)

if not result.ok:
    print(
        "F-004 invariant violated. Reference must reject behaviorally, the "
        "dead-guard variant must not, and the textual grep must pass on both.",
        file=sys.stderr,
    )
sys.exit(0 if result.ok else 1)
