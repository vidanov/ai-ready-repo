"""The generic F-004 dead-guard falsifier is portable across surfaces.

Step 1 of the falsifier-registry extraction: the runner in
scripts/falsifiers/dead_guard.py must work on a surface that is NOT the
discount example. If it only ever runs on apply_discount, it is not a registry
entry, it is a fixture with extra ceremony. These tests fill its slots with a
second, unrelated surface and require the same verdict.
"""

import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS / "falsifiers"))

import dead_guard as f004  # noqa: E402

SPECS_DIR = SCRIPTS / "falsifiers" / "specs"

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


# ── Step 2: portable specs run the same falsifier from data ──────────────────


def _load_spec(name: str) -> dict:
    return yaml.safe_load((SPECS_DIR / name).read_text())


def test_discount_spec_runs_from_data() -> None:
    """The discount example, expressed as a spec file, gives the F-004 verdict
    through run_from_spec -- no hardcoded Python slots."""
    result = f004.run_from_spec(_load_spec("dead_guard_discount.yaml"))
    assert result.ok is True
    assert result.reference_fires is True
    assert result.variant_is_dead is True


def test_withdrawal_spec_ports_f004_to_a_second_surface_via_data() -> None:
    """The portability claim at the spec level: an unrelated surface ports F-004
    by writing a spec and nothing else."""
    result = f004.run_from_spec(_load_spec("dead_guard_withdrawal.yaml"))
    assert result.ok is True
    assert result.reference_fires is True
    assert result.variant_is_dead is True


def test_spec_missing_key_is_spec_error_not_a_verdict() -> None:
    """A malformed spec is measurement_invalid, not a failed falsifier: the
    runner could not look. It raises rather than returning ok=False."""
    spec = _load_spec("dead_guard_discount.yaml")
    del spec["guard_pattern"]
    with pytest.raises(f004.SpecError):
        f004.run_from_spec(spec)


def test_spec_non_mapping_probe_input_is_spec_error() -> None:
    spec = _load_spec("dead_guard_discount.yaml")
    spec["probe_input"] = ["not", "a", "mapping"]
    with pytest.raises(f004.SpecError):
        f004.run_from_spec(spec)


def test_spec_entry_not_defined_in_source_is_spec_error() -> None:
    spec = _load_spec("dead_guard_discount.yaml")
    spec["entry"] = "not_the_function_name"
    with pytest.raises(f004.SpecError):
        f004.run_from_spec(spec)
