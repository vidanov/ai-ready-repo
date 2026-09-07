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


# ── Step 3: custody — content-addressed trust, refuse-to-exec unlisted ───────


def test_spec_id_is_stable_and_content_addressed() -> None:
    spec = _load_spec("dead_guard_discount.yaml")
    assert f004.spec_id(spec) == f004.spec_id(dict(spec))  # order-independent, stable


def test_spec_id_ignores_attribution_but_tracks_executed_bytes() -> None:
    """Editing an attribution line (name/source) must NOT change the id;
    changing an executed field MUST. The id covers exactly what gets exec'd."""
    spec = _load_spec("dead_guard_discount.yaml")
    base = f004.spec_id(spec)

    attribution_edit = dict(spec)
    attribution_edit["source"] = "someone else entirely"
    attribution_edit["name"] = "renamed"
    assert f004.spec_id(attribution_edit) == base  # attribution does not re-key

    executed_edit = dict(spec)
    executed_edit["guard_pattern"] = "different marker"
    assert f004.spec_id(executed_edit) != base  # executed change re-keys


def test_trusted_spec_runs() -> None:
    spec = _load_spec("dead_guard_discount.yaml")
    trusted = {f004.spec_id(spec)}
    result = f004.run_from_spec(spec, trusted_ids=trusted)
    assert result.ok is True


def test_untrusted_spec_is_refused_before_exec() -> None:
    """A well-formed spec whose id is not trusted must raise UntrustedSpecError,
    NOT run its source. This is the custody gate."""
    spec = _load_spec("dead_guard_discount.yaml")
    with pytest.raises(f004.UntrustedSpecError):
        f004.run_from_spec(spec, trusted_ids=set())  # empty trust = refuse all


def test_tampered_spec_loses_trust() -> None:
    """Approve a spec, then change one executed byte. The tampered spec's id no
    longer matches the trusted id, so it is refused -- a spec cannot smuggle new
    source under an old approval."""
    spec = _load_spec("dead_guard_discount.yaml")
    trusted = {f004.spec_id(spec)}  # approve the original

    tampered = dict(spec)
    tampered["reference_source"] = spec["reference_source"] + "\n# smuggled line\n"
    with pytest.raises(f004.UntrustedSpecError):
        f004.run_from_spec(tampered, trusted_ids=trusted)


def test_attribution_edit_keeps_trust() -> None:
    """The dual of the tamper test: re-attributing a trusted spec (changing only
    metadata) does not break its trust, because the id ignores attribution."""
    spec = _load_spec("dead_guard_discount.yaml")
    trusted = {f004.spec_id(spec)}
    reattributed = dict(spec)
    reattributed["source"] = "re-credited"
    result = f004.run_from_spec(reattributed, trusted_ids=trusted)
    assert result.ok is True


def test_first_party_manifest_trusts_shipped_specs() -> None:
    """The shipped trusted_specs.json must list both first-party specs, so they
    run under the real manifest, and an unlisted spec would not."""
    trusted = f004.load_trusted_ids(SPECS_DIR / "trusted_specs.json")
    for name in ("dead_guard_discount.yaml", "dead_guard_withdrawal.yaml"):
        spec = _load_spec(name)
        assert f004.spec_id(spec) in trusted
        assert f004.run_from_spec(spec, trusted_ids=trusted).ok is True


def test_missing_manifest_is_refuse_by_default() -> None:
    """No manifest means an empty trust set, not an error: nothing is trusted."""
    trusted = f004.load_trusted_ids(SPECS_DIR / "does_not_exist.json")
    assert trusted == set()
    spec = _load_spec("dead_guard_discount.yaml")
    with pytest.raises(f004.UntrustedSpecError):
        f004.run_from_spec(spec, trusted_ids=trusted)


def test_unreadable_manifest_is_spec_error(tmp_path: Path) -> None:
    bad = tmp_path / "trusted_specs.json"
    bad.write_text("{not json\n")
    with pytest.raises(f004.SpecError):
        f004.load_trusted_ids(bad)


def test_spec_id_on_spec_missing_executed_fields_is_spec_error() -> None:
    with pytest.raises(f004.SpecError):
        f004.spec_id({"entry": "f"})  # missing sources, probe_input, guard_pattern


def test_manifest_without_trusted_map_is_spec_error(tmp_path: Path) -> None:
    bad = tmp_path / "trusted_specs.json"
    bad.write_text('{"not_trusted": {}}\n')  # valid json, wrong shape
    with pytest.raises(f004.SpecError):
        f004.load_trusted_ids(bad)
