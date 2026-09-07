"""The generic F-004 dead-guard falsifier is portable across surfaces.

Step 1 of the falsifier-registry extraction: the runner in
scripts/falsifiers/dead_guard.py must work on a surface that is NOT the
discount example. If it only ever runs on apply_discount, it is not a registry
entry, it is a fixture with extra ceremony. These tests fill its slots with a
second, unrelated surface and require the same verdict.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS / "falsifiers"))

import dead_guard as f004  # noqa: E402

# ── A second surface, nothing to do with discounts: a withdrawal guard. ──────

REFERENCE_SRC = """
def withdraw(balance, amount):
    if amount > balance:
        raise ValueError("insufficient funds")
    if balance == 0:
        return 0
    return balance - amount
"""

# Dead variant: the guard is moved inside the balance==0 branch, so it never
# fires for the probe (a positive balance with an over-withdrawal).
DEAD_SRC = """
def withdraw(balance, amount):
    if balance == 0:
        if amount > balance:
            raise ValueError("insufficient funds")
        return 0
    return balance - amount
"""


def _load(src: str):
    ns: dict = {}
    exec(src, ns)  # noqa: S102 - fixed, local test source
    return ns["withdraw"]


def test_runner_confirms_dead_guard_on_a_second_surface() -> None:
    """The exact F-004 shape on a withdrawal guard, not a discount: reference
    fires, dead variant is silent, grep matches both, verdict ok."""
    result = f004.run(
        reference_fn=_load(REFERENCE_SRC),
        dead_variant_fn=_load(DEAD_SRC),
        probe_input={"balance": 100, "amount": 500},  # over-withdrawal on the executed path
        guard_pattern="raise ValueError",
        reference_source=REFERENCE_SRC,
        variant_source=DEAD_SRC,
    )
    assert result.reference_fires is True
    assert result.variant_is_dead is True
    assert result.grep_matches_both is True
    assert result.ok is True


def test_runner_falsifier_a_live_guard_variant_is_not_dead() -> None:
    """Falsifier of the abstraction: if the 'dead' variant actually still
    guards (guard on the executed path), the runner must NOT report it dead,
    and the verdict must be False. This proves the runner tests the slots
    rather than always returning ok."""
    live_variant = REFERENCE_SRC  # same as reference: guard is live, not dead
    result = f004.run(
        reference_fn=_load(REFERENCE_SRC),
        dead_variant_fn=_load(live_variant),
        probe_input={"balance": 100, "amount": 500},
        guard_pattern="raise ValueError",
        reference_source=REFERENCE_SRC,
        variant_source=live_variant,
    )
    assert result.reference_fires is True
    assert result.variant_is_dead is False  # the variant guarded -> not dead
    assert result.ok is False  # so the F-004 demonstration does not hold


def test_runner_falsifier_missing_grep_pattern_fails() -> None:
    """If the guard pattern is absent from the sources, the grep step cannot
    match both and the demonstration does not hold -- the runner does not
    fabricate a match."""
    result = f004.run(
        reference_fn=_load(REFERENCE_SRC),
        dead_variant_fn=_load(DEAD_SRC),
        probe_input={"balance": 100, "amount": 500},
        guard_pattern="this-string-is-in-neither-source",
        reference_source=REFERENCE_SRC,
        variant_source=DEAD_SRC,
    )
    assert result.grep_matches_both is False
    assert result.ok is False
