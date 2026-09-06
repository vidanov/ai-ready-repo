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
