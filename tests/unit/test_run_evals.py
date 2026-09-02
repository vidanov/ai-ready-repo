"""Output-shape tests for the eval runner's per-task receipt.

These guard the EvalReceipt refactor: the result of run_task() must carry a
stable set of fields on every path (success, load error, measurement-invalid),
so a downstream reader — especially the aggregate that enforces the
measurement_invalid output-space invariant (1f916 #3539) — never reads a
missing key. Before the refactor, the three error-return paths hand-built
dicts that omitted verdict/reachable/executed, silently exempting load-error
rows from the invariant. These tests pin the contract closed.

Also the first coverage of scripts/ (CONTRIBUTING #023).
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_evals  # noqa: E402

# Every receipt, whatever the path, must expose these keys.
RECEIPT_KEYS = {
    "task",
    "passed",
    "verify_pass",
    "reason_match",
    "done_condition_ok",
    "tests_disabled",
    "protected_touched",
    "diff_lines",
    "changed_files",
    "elapsed",
    "origin",
    "attempts_to_green",
    "canonical_entry_point",
    "reachable",
    "executed",
    "verdict",
    "door",
    "exit_code",
    "stdout",
    "stderr",
}

VALID_VERDICTS = {
    run_evals.VERDICT_RAN_PASSED,
    run_evals.VERDICT_RAN_FAILED,
    run_evals.VERDICT_MEASUREMENT_INVALID,
}


def _write_task(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / f"{name}.yaml"
    p.write_text(body)
    return p


def test_passing_task_has_full_receipt(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path,
        "ok",
        'description: "x"\nverification: "true"\nexpected_exit_code: 0\norigin: birth\n',
    )
    r = run_evals.run_task(task)
    assert RECEIPT_KEYS <= set(r), f"missing keys: {RECEIPT_KEYS - set(r)}"
    assert r["verdict"] == run_evals.VERDICT_RAN_PASSED
    assert r["reachable"] is True and r["executed"] is True
    assert r["verdict"] in VALID_VERDICTS


def test_missing_door_is_measurement_invalid(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path,
        "corpse",
        'description: "x"\nverification: "no_such_cmd_zzq_1916"\n'
        "expected_exit_code: 0\norigin: birth\n",
    )
    r = run_evals.run_task(task)
    assert r["verdict"] == run_evals.VERDICT_MEASUREMENT_INVALID
    assert r["reachable"] is False
    assert r["executed"] is False
    assert r["exit_code"] == 127
    # A corpse is not a pass.
    assert r["passed"] is False


def test_load_error_receipt_is_complete_and_invalid(tmp_path: Path) -> None:
    """A file that cannot parse carries no evidence about the subject.

    It must expose the full receipt shape AND classify as measurement_invalid,
    not slip through with a partial dict that the aggregate reads as an
    ordinary failure. This is the stale-error-dict gap the refactor closes.
    """
    task = _write_task(tmp_path, "broken", "this: is: not: valid: yaml: {[\n")
    r = run_evals.run_task(task)
    assert "load_error" in r
    assert RECEIPT_KEYS <= set(r), f"missing keys: {RECEIPT_KEYS - set(r)}"
    assert r["verdict"] == run_evals.VERDICT_MEASUREMENT_INVALID
    assert r["passed"] is False


def test_missing_required_field_receipt_is_complete(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path, "incomplete", 'description: "no verification field"\norigin: birth\n'
    )
    r = run_evals.run_task(task)
    assert "load_error" in r
    assert RECEIPT_KEYS <= set(r), f"missing keys: {RECEIPT_KEYS - set(r)}"
    assert r["verdict"] == run_evals.VERDICT_MEASUREMENT_INVALID


def test_classify_run_disjoint_verdicts() -> None:
    assert run_evals.classify_run(0, 0) == (True, True, run_evals.VERDICT_RAN_PASSED)
    assert run_evals.classify_run(1, 0) == (True, True, run_evals.VERDICT_RAN_FAILED)
    assert run_evals.classify_run(127, 0) == (
        False,
        False,
        run_evals.VERDICT_MEASUREMENT_INVALID,
    )
    assert run_evals.classify_run(126, 0) == (
        False,
        False,
        run_evals.VERDICT_MEASUREMENT_INVALID,
    )
    # expected nonzero exit still passes when it matches
    assert run_evals.classify_run(2, 2) == (True, True, run_evals.VERDICT_RAN_PASSED)


def test_canonical_entry_point() -> None:
    assert run_evals.uses_canonical_entry_point("make verify") is True
    assert run_evals.uses_canonical_entry_point("  make test-unit ") is True
    assert run_evals.uses_canonical_entry_point("pytest tests/") is False
    assert run_evals.uses_canonical_entry_point("uv run python x.py") is False


def test_replay_fixtures_pin_the_invariant() -> None:
    """The golden receipts (jerry's durability request, 1f916 #3539) must keep
    measurement_invalid disjoint from pass/fail. If a schema change collapses
    the verdict space, these break instead of a dead check hiding for days."""
    import json

    fixtures = SCRIPTS / "eval_tasks" / "fixtures"
    missing = json.loads((fixtures / "replay-missing-door.json").read_text())
    restored = json.loads((fixtures / "replay-restored-door.json").read_text())

    assert missing["verdict"] == run_evals.VERDICT_MEASUREMENT_INVALID
    assert missing["reachable"] is False
    assert missing["executed"] is False
    assert missing["exit_code"] == 127
    assert missing["passed"] is False  # a corpse is never a pass

    assert restored["verdict"] == run_evals.VERDICT_RAN_PASSED
    assert restored["reachable"] is True
    assert restored["passed"] is True

    # The invariant: the two verdicts are distinct values, not one bit.
    assert missing["verdict"] != restored["verdict"]
