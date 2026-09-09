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

import pytest

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


def test_newly_invalid_row_is_a_regression() -> None:
    """#034 second acceptance condition (Current, 1f916 c43166): a task that was
    measurable at baseline and is measurement_invalid now is a newly-dead row.
    It must be flagged even when the surviving tasks still pass."""
    baseline_invalid: list[str] = []  # everything was measurable at baseline
    current = ["repository-verification.yaml"]  # this one died since
    assert run_evals.newly_invalid_rows(current, baseline_invalid) == [
        "repository-verification.yaml"
    ]


def test_row_invalid_at_baseline_is_not_a_new_regression() -> None:
    """A row that was already invalid at baseline is a known gap, not a new
    corpse. It must not re-fire on every run (that would be a stuck alarm)."""
    baseline_invalid = ["known-gap.yaml"]
    current = ["known-gap.yaml"]
    assert run_evals.newly_invalid_rows(current, baseline_invalid) == []


def test_new_task_invalid_on_arrival_is_flagged() -> None:
    """A brand-new task that is invalid on arrival is flagged as a new corpse.
    This is deliberate: it forces an explicit baseline update rather than
    letting a new dead row slip in unnoticed. Only a row already invalid at
    baseline (a known gap) is exempt."""
    baseline_invalid = ["known-gap.yaml"]
    current = ["known-gap.yaml", "brand-new.yaml"]
    assert run_evals.newly_invalid_rows(current, baseline_invalid) == ["brand-new.yaml"]


def test_invalid_task_names_extracts_only_measurement_invalid() -> None:
    results = [
        {"task": "a.yaml", "verdict": run_evals.VERDICT_RAN_PASSED},
        {"task": "b.yaml", "verdict": run_evals.VERDICT_MEASUREMENT_INVALID},
        {"task": "c.yaml", "verdict": run_evals.VERDICT_RAN_FAILED},
        {"task": "d.yaml", "verdict": run_evals.VERDICT_MEASUREMENT_INVALID},
    ]
    assert run_evals.invalid_task_names(results) == ["b.yaml", "d.yaml"]


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


def test_cli_success_reports_which_prior_was_checked(tmp_path, monkeypatch, capsys):
    # prior_state_observed as a visible fact (1f916 #4454, zola): a clean run
    # must name which prior the newly-invalid check ran against, not leave the
    # reader to infer it from a bare success line.
    _cli_fixture(tmp_path, monkeypatch, command="true")
    assert run_evals.main() == 0
    out = capsys.readouterr().out
    assert "prior:" in out
    assert "committed known_invalid.json" in out
    assert "newly-invalid-row check enforced" in out


def test_cli_newly_invalid_row_fails_above_coverage_floor(tmp_path, monkeypatch):
    """#034 second acceptance condition, end to end and above the floor: three
    tasks pass and one is newly measurement_invalid, so coverage is 3/4 = 75%
    (at the floor, not below it). The coverage gate does NOT fire. The run must
    still fail -- on the newly-dead row, the case the floor is blind to. This is
    the branch the floor cannot reach (Current, 1f916 c43166)."""
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    for name in ("a", "b", "c"):
        (tasks / f"{name}.yaml").write_text(
            'description: ok\nverification: "true"\nexpected_exit_code: 0\norigin: birth\n'
        )
    # d was measurable at baseline; its door is unreachable now -> invalid.
    (tasks / "d.yaml").write_text(
        'description: dead\nverification: "definitely-not-a-command"\n'
        "expected_exit_code: 0\norigin: birth\n"
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"success_rate": 1.0, "tasks": 4, "measurement_invalid_tasks": []}')
    monkeypatch.setattr(run_evals, "TASKS_DIR", tasks)
    monkeypatch.setattr(run_evals, "BASELINE_FILE", baseline)
    monkeypatch.setattr(run_evals, "get_diff_stats", lambda: (0, []))
    monkeypatch.setattr(run_evals, "count_tests_disabled_in_diff", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["run_evals.py"])

    assert run_evals.main() == 1


def test_cli_no_baseline_invalid_set_prints_skip_note(tmp_path, monkeypatch, capsys):
    """The newly-invalid check skips only when there is no trusted prior at all:
    the committed known_invalid.json is absent AND the runtime baseline has no
    invalid-row set. Then it says so rather than passing silently."""
    baseline = _cli_fixture(tmp_path, monkeypatch, command="true")
    baseline.write_text('{"success_rate": 1.0, "tasks": 1}')  # no measurement_invalid_tasks
    # No committed trusted prior either.
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", tmp_path / "absent.json")
    assert run_evals.main() == 0
    assert "newly-invalid-row regression check skipped" in capsys.readouterr().out


def test_cli_committed_prior_enforces_the_check(tmp_path, monkeypatch, capsys):
    """With the committed trusted prior present (empty accepted-dead set) and a
    passing task, the check runs -- not skipped -- and the run passes. This is
    the enforced-in-CI path: a trusted prior exists, so the check has teeth."""
    baseline = _cli_fixture(tmp_path, monkeypatch, command="true")
    baseline.write_text('{"success_rate": 1.0, "tasks": 1}')
    prior = tmp_path / "known_invalid.json"
    prior.write_text('{"measurement_invalid_tasks": []}')
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", prior)
    assert run_evals.main() == 0
    out = capsys.readouterr().out
    assert "newly-invalid-row regression check skipped" not in out


def test_cli_known_invalid_row_does_not_refire(tmp_path, monkeypatch):
    """A row already invalid at baseline is a known gap; newly_invalid_rows
    returns [] for it, so it does not add a second failure."""
    assert run_evals.newly_invalid_rows(["check.yaml"], ["check.yaml"]) == []


def test_cli_missing_tasks_fails(tmp_path, monkeypatch):
    _cli_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(run_evals, "TASKS_DIR", tmp_path / "missing")
    assert run_evals.main() == 1


def test_load_known_invalid_missing_file_is_none(tmp_path, monkeypatch) -> None:
    """A missing trusted-prior file means 'cannot compare', distinct from an
    empty reviewed set. The caller must be able to tell them apart, so a missing
    file returns None (skip), not [] (fail on any corpse)."""
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", tmp_path / "absent.json")
    assert run_evals.load_known_invalid() is None


def test_load_known_invalid_empty_is_a_real_prior(tmp_path, monkeypatch) -> None:
    """An empty reviewed set is a real prior: nothing is accepted-dead, so any
    invalid row is a regression. It must return [] (compare), not None (skip)."""
    f = tmp_path / "known_invalid.json"
    f.write_text('{"measurement_invalid_tasks": []}')
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", f)
    assert run_evals.load_known_invalid() == []


def test_load_known_invalid_reads_accepted_rows(tmp_path, monkeypatch) -> None:
    f = tmp_path / "known_invalid.json"
    f.write_text('{"measurement_invalid_tasks": ["known-gap.yaml"]}')
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", f)
    assert run_evals.load_known_invalid() == ["known-gap.yaml"]


def test_committed_known_invalid_file_is_valid() -> None:
    """The shipped trusted prior must load and be a real (list) prior, so the
    newly-invalid check is enforced in CI rather than skipped."""
    assert run_evals.load_known_invalid() == []


def test_load_known_invalid_truncated_fails_closed(tmp_path, monkeypatch):
    """zola's falsifier (1f916 #4266): truncate the predecessor and the same
    green must not survive. A present-but-truncated prior fails closed, it does
    not degrade to an empty prior."""
    f = tmp_path / "known_invalid.json"
    f.write_text('{"measurement_invalid_tasks": [')  # truncated JSON
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", f)
    with pytest.raises(run_evals.TrustedPriorError):
        run_evals.load_known_invalid()


def test_load_known_invalid_wrong_shape_fails_closed(tmp_path, monkeypatch):
    """A file that parses but has no measurement_invalid_tasks list is malformed,
    not an empty prior. Treating garbage as [] would fail open."""
    f = tmp_path / "known_invalid.json"
    f.write_text("42")  # valid JSON, wrong shape
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", f)
    with pytest.raises(run_evals.TrustedPriorError):
        run_evals.load_known_invalid()


def test_cli_broken_prior_fails_closed(tmp_path, monkeypatch, capsys):
    """End to end: a passing run with a present-but-broken trusted prior must
    return non-zero, not pass by treating the broken prior as empty."""
    baseline = _cli_fixture(tmp_path, monkeypatch, command="true")
    baseline.write_text('{"success_rate": 1.0, "tasks": 1}')
    broken = tmp_path / "known_invalid.json"
    broken.write_text('{"measurement_invalid_tasks": [')  # truncated
    monkeypatch.setattr(run_evals, "KNOWN_INVALID_FILE", broken)
    assert run_evals.main() == 1
    assert "fails closed" in capsys.readouterr().out
