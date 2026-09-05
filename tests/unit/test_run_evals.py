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


# ── Measurement coverage (jerry c37451 + latex c37440, 1f916 #3539) ──────────
# Dropping measurement_invalid from the pass/fail denominator is correct
# (disjointness), but on its own it lets the rate read 100% as the harness
# rots: 9 corpses + 1 pass reports 1/1. Coverage is the unomittable companion
# field, and a floor makes the run refuse to call a low-coverage rate healthy.


def _receipt(verdict: str, passed: bool = False, load_error: str | None = None) -> dict:
    """Minimal receipt for aggregate() tests."""
    r = run_evals.EvalReceipt(task="t", verdict=verdict).to_dict()
    r["passed"] = passed
    if load_error is not None:
        r["load_error"] = load_error
    return r


def test_aggregate_reports_coverage() -> None:
    results = [
        _receipt(run_evals.VERDICT_RAN_PASSED, passed=True),
        _receipt(run_evals.VERDICT_RAN_PASSED, passed=True),
        _receipt(run_evals.VERDICT_MEASUREMENT_INVALID),
    ]
    agg = run_evals.aggregate(results)
    # pass rate is over measurable tasks only: 2/2
    assert agg.passed == 2
    assert agg.total == 2
    assert agg.rate == 1.0
    # coverage is over ALL runs: 2 of 3 measurements were valid
    assert agg.valid_runs == 2
    assert agg.total_runs == 3
    assert agg.coverage == 2 / 3


def test_coverage_floor_fails_a_rotting_harness() -> None:
    """The launder case latex named: nine corpses and one pass. Pass rate is
    100% but coverage is 10% — the aggregate must refuse to call it healthy."""
    results = [_receipt(run_evals.VERDICT_RAN_PASSED, passed=True)]
    results += [_receipt(run_evals.VERDICT_MEASUREMENT_INVALID) for _ in range(9)]
    agg = run_evals.aggregate(results)
    assert agg.rate == 1.0  # technically 1/1
    assert agg.coverage == 0.1
    assert agg.coverage_ok is False  # below floor — not healthy


def test_full_coverage_passes_floor() -> None:
    results = [
        _receipt(run_evals.VERDICT_RAN_PASSED, passed=True),
        _receipt(run_evals.VERDICT_RAN_FAILED, passed=False),
    ]
    agg = run_evals.aggregate(results)
    assert agg.coverage == 1.0
    assert agg.coverage_ok is True


def test_load_errors_count_against_coverage() -> None:
    """A file that cannot load is measurement_invalid too — it lowers coverage,
    it is not silently dropped."""
    results = [
        _receipt(run_evals.VERDICT_RAN_PASSED, passed=True),
        _receipt(run_evals.VERDICT_MEASUREMENT_INVALID, load_error="bad yaml"),
    ]
    agg = run_evals.aggregate(results)
    assert agg.valid_runs == 1
    assert agg.total_runs == 2
    assert agg.coverage == 0.5


def test_coverage_floor_constant_exists() -> None:
    assert 0.0 < run_evals.MEASUREMENT_COVERAGE_FLOOR <= 1.0


# ── Required axes: two-stage coverage gate (axiom-sovereign, 1f916 #3595) ────
# A scalar coverage floor measures prevalence (how many runs were valid) but
# cannot establish that the required DIMENSIONS for this object were exercised.
# The required set is declared on the TASK (the object type), not the receipt,
# so a receipt cannot pass by silently omitting an axis. Stage 1 rejects any
# receipt with an unexercised required axis (missing_required_axes, disjoint
# from pass/fail like measurement_invalid); stage 2 scores what remains.


def test_exercised_axes_recorded_from_real_evidence(tmp_path) -> None:
    """A task that checks reason + done_condition records those axes as
    exercised; reachability is exercised whenever the subject actually ran."""
    task = tmp_path / "t.yaml"
    task.write_text(
        'description: "x"\n'
        'verification: "echo WHY_TAG"\n'
        "expected_exit_code: 0\n"
        'expected_reason: "WHY_TAG"\n'
        'done_condition: "true"\n'
        "origin: birth\n"
    )
    r = run_evals.run_task(task)
    axes = set(r["exercised_axes"])
    assert "reachability" in axes
    assert "reason" in axes
    assert "done_condition" in axes


def test_unexercised_axis_not_recorded(tmp_path) -> None:
    """A task that declares no reason check does not claim the reason axis."""
    task = tmp_path / "t.yaml"
    task.write_text(
        'description: "x"\nverification: "true"\nexpected_exit_code: 0\norigin: birth\n'
    )
    r = run_evals.run_task(task)
    assert "reason" not in set(r["exercised_axes"])


def test_missing_required_axis_rejected_before_scoring(tmp_path, monkeypatch) -> None:
    """Stage 1: a task requires the reason axis but never exercises it. The
    receipt must be rejected as missing_required_axes, NOT scored as a pass."""
    # Isolate from the ambient working tree (#034): run_task reads the real git
    # diff via get_diff_stats, so an uncommitted protected-path edit would flip
    # protected_touched and fail this axis test for a reason outside its body.
    monkeypatch.setattr(run_evals, "get_diff_stats", lambda: (0, []))
    task = tmp_path / "t.yaml"
    task.write_text(
        'description: "x"\n'
        'verification: "true"\n'  # passes, but no expected_reason -> reason axis not exercised
        "expected_exit_code: 0\n"
        "required_axes: [reachability, reason]\n"
        "origin: birth\n"
    )
    r = run_evals.run_task(task)
    assert r["missing_required_axes"] == ["reason"]
    assert r["passed"] is False
    # disjoint from ordinary pass/fail, like measurement_invalid
    assert r["verdict"] == run_evals.VERDICT_MEASUREMENT_INVALID


def test_all_required_axes_exercised_proceeds_to_scoring(tmp_path, monkeypatch) -> None:
    # Isolate from the ambient working tree (#034): see the sibling test above.
    monkeypatch.setattr(run_evals, "get_diff_stats", lambda: (0, []))
    task = tmp_path / "t.yaml"
    task.write_text(
        'description: "x"\n'
        'verification: "echo WHY_TAG"\n'
        "expected_exit_code: 0\n"
        'expected_reason: "WHY_TAG"\n'
        "required_axes: [reachability, reason]\n"
        "origin: birth\n"
    )
    r = run_evals.run_task(task)
    assert r["missing_required_axes"] == []
    assert r["passed"] is True
    assert r["verdict"] == run_evals.VERDICT_RAN_PASSED


def test_aggregate_excludes_missing_axis_from_rate() -> None:
    """A receipt rejected for a missing required axis is measurement_invalid:
    it must not be averaged into the pass rate (axiom-sovereign's phrase)."""
    good = _receipt(run_evals.VERDICT_RAN_PASSED, passed=True)
    good["missing_required_axes"] = []
    missing = _receipt(run_evals.VERDICT_MEASUREMENT_INVALID)
    missing["missing_required_axes"] = ["reason"]
    agg = run_evals.aggregate([good, missing])
    assert agg.passed == 1
    assert agg.total == 1  # missing-axis row is out of the pass/fail denominator
    assert agg.rate == 1.0
    assert agg.coverage == 0.5  # but it counts against coverage


def _cli_fixture(tmp_path, monkeypatch, command="false", baseline=False):
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "check.yaml").write_text(
        f'description: Check\nverification: "{command}"\nexpected_exit_code: 0\norigin: birth\n'
    )
    baseline_file = tmp_path / "baseline.json"
    monkeypatch.setattr(run_evals, "TASKS_DIR", tasks)
    monkeypatch.setattr(run_evals, "BASELINE_FILE", baseline_file)
    monkeypatch.setattr(run_evals, "get_diff_stats", lambda: (0, []))
    monkeypatch.setattr(run_evals, "count_tests_disabled_in_diff", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["run_evals.py"] + (["--baseline"] if baseline else []))
    return baseline_file


def test_cli_failing_task_without_baseline_fails(tmp_path, monkeypatch):
    _cli_fixture(tmp_path, monkeypatch)
    assert run_evals.main() == 1


def test_cli_failed_run_cannot_replace_baseline(tmp_path, monkeypatch):
    baseline = _cli_fixture(tmp_path, monkeypatch, baseline=True)
    original = '{"success_rate": 1.0, "tasks": 1}'
    baseline.write_text(original)
    assert run_evals.main() == 1
    assert baseline.read_text() == original


def test_cli_invalid_measurement_cannot_create_baseline(tmp_path, monkeypatch):
    baseline = _cli_fixture(tmp_path, monkeypatch, command="exit 127", baseline=True)
    assert run_evals.main() == 1
    assert not baseline.exists()


def test_cli_success_can_create_baseline(tmp_path, monkeypatch):
    baseline = _cli_fixture(tmp_path, monkeypatch, command="true", baseline=True)
    assert run_evals.main() == 0
    assert baseline.exists()


def test_cli_missing_tasks_fails(tmp_path, monkeypatch):
    _cli_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(run_evals, "TASKS_DIR", tmp_path / "missing")
    assert run_evals.main() == 1
