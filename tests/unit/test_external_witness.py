"""Focused coverage for the disjoint external-witness freshness path."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_reader  # noqa: E402
import referent_liveness  # noqa: E402


def _write_task(directory: Path, name: str, body: str) -> None:
    (directory / name).write_text(body)


def test_external_reader_reads_quoted_unquoted_and_missing_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_task(tmp_path, "double.yaml", 'verification: "make verify"\n')
    _write_task(tmp_path, "single.yaml", "verification: 'uv run python scripts/check.py'\n")
    _write_task(tmp_path, "bare.yaml", "verification: make verify-fast\n")
    _write_task(tmp_path, "missing.yaml", "description: no verification field\n")

    monkeypatch.setattr(external_reader, "EVAL_TASKS_DIR", tmp_path)

    assert external_reader._read_tasks() == {
        "bare.yaml": "make verify-fast",
        "double.yaml": "make verify",
        "missing.yaml": "",
        "single.yaml": "uv run python scripts/check.py",
    }


def test_external_reader_record_write_failure_is_measurement_invalid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class BrokenRecord:
        def write_text(self, _text: str) -> None:
            raise OSError("disk full")

    monkeypatch.setattr(external_reader, "_read_tasks", lambda: {"task.yaml": "make verify"})
    monkeypatch.setattr(external_reader, "READER_RECORD", BrokenRecord())

    assert external_reader.record(now=123.0) == external_reader.EXIT_MEASUREMENT_INVALID
    assert "MEASUREMENT_INVALID: disk full" in capsys.readouterr().out


def test_external_reader_check_unreadable_record_is_measurement_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = tmp_path / "reader_witness.json"
    record.write_text("{not json\n")
    monkeypatch.setattr(external_reader, "READER_RECORD", record)

    assert external_reader.check(now=123.0) == external_reader.EXIT_MEASUREMENT_INVALID
    assert "external_reader: INVALID" in capsys.readouterr().out


def test_external_reader_check_rejects_boolean_task_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = tmp_path / "reader_witness.json"
    record.write_text('{"reader_observed_at": 123.0, "task_count": true, "tasks": {}}\n')
    monkeypatch.setattr(external_reader, "READER_RECORD", record)

    assert external_reader.check(now=123.0) == external_reader.EXIT_MEASUREMENT_INVALID
    assert "task_count missing or not an integer" in capsys.readouterr().out


def test_referent_liveness_rejects_external_witness_task_count_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = tmp_path / "reader_witness.json"
    now = 1000.0
    record.write_text('{"reader_observed_at": 1000.0, "task_count": 9, "tasks": {}}\n')
    monkeypatch.setattr(referent_liveness, "READER_RECORD", record)

    ok, message = referent_liveness.check_external_witness(
        manifest_verified_at=now,
        expected_task_count=3,
        now=now,
    )

    assert ok is False
    assert "current surface has 3" in message


def test_referent_liveness_rejects_boolean_task_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = tmp_path / "reader_witness.json"
    record.write_text('{"reader_observed_at": 1000.0, "task_count": true, "tasks": {}}\n')
    monkeypatch.setattr(referent_liveness, "READER_RECORD", record)

    ok, message = referent_liveness.check_external_witness(
        manifest_verified_at=1000.0,
        expected_task_count=1,
        now=1000.0,
    )

    assert ok is False
    assert "task_count missing or not an integer" in message


def test_referent_liveness_rejects_boundary_disagreement_when_count_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """zola's falsifier (1f916 #3997, c43086): serve a valid hash while
    withholding the ref. Count matches, timestamp fresh, but the referent the
    reader observed differs from the runner's claim. A matching door count is
    not a matching door set -- the gate must fail.
    """
    record = tmp_path / "reader_witness.json"
    now = 1000.0
    # Reader independently observed task_b pointing at a DIFFERENT command than
    # the runner claims. Same count (2), same timestamp. Only the content differs.
    record.write_text(
        '{"reader_observed_at": 1000.0, "task_count": 2, '
        '"tasks": {"a.yaml": "make verify", "b.yaml": "make verify-fast"}}\n'
    )
    monkeypatch.setattr(referent_liveness, "READER_RECORD", record)

    ok, message = referent_liveness.check_external_witness(
        manifest_verified_at=now,
        expected_task_count=2,
        now=now,
        expected_referents={"a.yaml": "make verify", "b.yaml": "make DIFFERENT"},
    )

    assert ok is False
    assert "referent boundary" in message
    assert "drifted=['b.yaml']" in message


def test_referent_liveness_accepts_matching_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: identical referent content, count, and fresh time
    pass. Without this, the falsifier above could pass by always failing.
    """
    record = tmp_path / "reader_witness.json"
    now = 1000.0
    record.write_text(
        '{"reader_observed_at": 1000.0, "task_count": 2, '
        '"tasks": {"a.yaml": "make verify", "b.yaml": "make verify-fast"}}\n'
    )
    monkeypatch.setattr(referent_liveness, "READER_RECORD", record)

    ok, message = referent_liveness.check_external_witness(
        manifest_verified_at=now,
        expected_task_count=2,
        now=now,
        expected_referents={"a.yaml": "make verify", "b.yaml": "make verify-fast"},
    )

    assert ok is True
    assert "external witness present" in message


def test_referent_liveness_rejects_reader_missing_referent_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the reader recorded no per-task map at all, a content comparison
    cannot be made: the witness fails rather than silently skipping the check.
    """
    record = tmp_path / "reader_witness.json"
    now = 1000.0
    record.write_text('{"reader_observed_at": 1000.0, "task_count": 1}\n')
    monkeypatch.setattr(referent_liveness, "READER_RECORD", record)

    ok, message = referent_liveness.check_external_witness(
        manifest_verified_at=now,
        expected_task_count=1,
        now=now,
        expected_referents={"a.yaml": "make verify"},
    )

    assert ok is False
    assert "no per-task referent map" in message


def test_referent_liveness_invalid_manifest_is_measurement_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "referent_manifest.json"
    manifest.write_text("{not json\n")
    monkeypatch.setattr(referent_liveness, "MANIFEST", manifest)
    monkeypatch.setattr(
        referent_liveness,
        "walk",
        lambda: [
            referent_liveness.ReferentResult(
                "task.yaml",
                "make verify",
                referent_liveness.LIVE,
                "make target exists: verify",
            )
        ],
    )

    assert referent_liveness.main([]) == referent_liveness.EXIT_MEASUREMENT_INVALID
    assert "MEASUREMENT_INVALID" in capsys.readouterr().out


# ── classify(): the five referent-resolution branches ───────────────────────


def test_classify_live_script_referent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(referent_liveness, "REPO_ROOT", tmp_path)
    (tmp_path / "check.py").write_text("print('x')\n")
    status, detail = referent_liveness.classify("uv run python check.py", set())
    assert status == referent_liveness.LIVE
    assert "script exists" in detail


def test_classify_stale_script_referent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(referent_liveness, "REPO_ROOT", tmp_path)
    status, detail = referent_liveness.classify("uv run python gone.py", set())
    assert status == referent_liveness.STALE_OR_DRIFTED
    assert "script referent gone" in detail


def test_classify_python_names_no_script() -> None:
    status, detail = referent_liveness.classify("uv run python", set())
    assert status == referent_liveness.REFERENT_MISMATCH
    assert "names no script" in detail


def test_classify_live_and_stale_make_target() -> None:
    live_status, live_detail = referent_liveness.classify("make verify", {"verify"})
    assert live_status == referent_liveness.LIVE
    assert "make target exists" in live_detail

    stale_status, stale_detail = referent_liveness.classify("make gone", {"verify"})
    assert stale_status == referent_liveness.STALE_OR_DRIFTED
    assert "make target referent gone" in stale_detail


def test_classify_empty_and_unrecognized_are_mismatch() -> None:
    empty_status, _ = referent_liveness.classify("", set())
    assert empty_status == referent_liveness.REFERENT_MISMATCH

    weird_status, weird_detail = referent_liveness.classify("bash run.sh", set())
    assert weird_status == referent_liveness.REFERENT_MISMATCH
    assert "unrecognized referent form" in weird_detail


# ── check_freshness(): jerry's freshness marker branches ─────────────────────


def test_check_freshness_missing_manifest_is_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(referent_liveness, "MANIFEST", tmp_path / "absent.json")
    fresh, message = referent_liveness.check_freshness(now=1000.0)
    assert fresh is False
    assert "never verified" in message


def test_check_freshness_non_numeric_verified_at_is_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "m.json"
    manifest.write_text('{"verified_at": "yesterday"}\n')
    monkeypatch.setattr(referent_liveness, "MANIFEST", manifest)
    fresh, message = referent_liveness.check_freshness(now=1000.0)
    assert fresh is False
    assert "no numeric verified_at" in message


def test_check_freshness_old_manifest_fails_on_age(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "m.json"
    manifest.write_text('{"verified_at": 0.0}\n')
    monkeypatch.setattr(referent_liveness, "MANIFEST", manifest)
    # now is far past MAX_AGE_DAYS after epoch
    old_now = referent_liveness.MAX_AGE_DAYS * 86400 * 2
    fresh, message = referent_liveness.check_freshness(now=old_now)
    assert fresh is False
    assert "manifest stale" in message


def test_check_freshness_recent_manifest_is_fresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "m.json"
    manifest.write_text('{"verified_at": 1000.0}\n')
    monkeypatch.setattr(referent_liveness, "MANIFEST", manifest)
    fresh, message = referent_liveness.check_freshness(now=1000.0)
    assert fresh is True
    assert "manifest fresh" in message


# ── walk(): surface enumeration and its measurement-invalid guards ───────────


def test_walk_missing_dir_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(referent_liveness, "EVAL_TASKS_DIR", tmp_path / "nope")
    with pytest.raises(FileNotFoundError):
        referent_liveness.walk()


def test_walk_empty_dir_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(referent_liveness, "EVAL_TASKS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        referent_liveness.walk()


def test_walk_classifies_each_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_task(tmp_path, "a.yaml", 'verification: "make verify"\n')
    _write_task(tmp_path, "b.yaml", "verification: make gone\n")
    monkeypatch.setattr(referent_liveness, "EVAL_TASKS_DIR", tmp_path)
    monkeypatch.setattr(referent_liveness, "_make_targets", lambda: {"verify"})

    results = referent_liveness.walk()
    by_task = {r.task: r.status for r in results}
    assert by_task["a.yaml"] == referent_liveness.LIVE
    assert by_task["b.yaml"] == referent_liveness.STALE_OR_DRIFTED


# ── external_reader: record success and check freshness branches ─────────────


def test_external_reader_record_writes_and_check_reads_fresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks_dir = tmp_path / "eval_tasks"
    tasks_dir.mkdir()
    (tasks_dir / "a.yaml").write_text('verification: "make verify"\n')
    record_path = tasks_dir / "reader_witness.json"
    monkeypatch.setattr(external_reader, "EVAL_TASKS_DIR", tasks_dir)
    monkeypatch.setattr(external_reader, "READER_RECORD", record_path)

    assert external_reader.record(now=1000.0) == external_reader.EXIT_OK
    assert record_path.is_file()

    # A record read at the same instant is FRESH.
    assert external_reader.check(now=1000.0) == external_reader.EXIT_OK
    assert "FRESH" in capsys.readouterr().out


def test_external_reader_check_absent_record_is_stale_or_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(external_reader, "READER_RECORD", tmp_path / "absent.json")
    assert external_reader.check(now=1000.0) == external_reader.EXIT_STALE_OR_ABSENT
    assert "ABSENT" in capsys.readouterr().out


def test_external_reader_check_stale_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = tmp_path / "reader_witness.json"
    record.write_text('{"reader_observed_at": 0.0, "task_count": 1, "tasks": {}}\n')
    monkeypatch.setattr(external_reader, "READER_RECORD", record)
    stale_now = external_reader.MAX_DRIFT_SECONDS * 2
    assert external_reader.check(now=stale_now) == external_reader.EXIT_STALE_OR_ABSENT
    assert "STALE" in capsys.readouterr().out


def test_external_reader_check_missing_observed_at_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = tmp_path / "reader_witness.json"
    record.write_text('{"task_count": 1, "tasks": {}}\n')
    monkeypatch.setattr(external_reader, "READER_RECORD", record)
    assert external_reader.check(now=1000.0) == external_reader.EXIT_MEASUREMENT_INVALID
    assert "reader_observed_at missing" in capsys.readouterr().out


def test_external_reader_main_dispatches_check_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(external_reader, "READER_RECORD", tmp_path / "absent.json")
    # --check on an absent record returns the stale/absent code, not record()
    assert external_reader.main(["--check"]) == external_reader.EXIT_STALE_OR_ABSENT
