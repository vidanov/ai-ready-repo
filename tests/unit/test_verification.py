"""Drills must preserve dirty workspaces and verification must retain failures."""

import subprocess
import sys
from pathlib import Path

import pytest

from ai_ready.verification.runner import verify
from ai_ready.verification.sandbox import run_isolated


def test_drill_preserves_dirty_and_untracked_files_on_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"uncommitted work\x00\xff")
    nested = tmp_path / "untracked"
    nested.mkdir()
    (nested / "note.txt").write_text("keep me")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = run_isolated(
        tmp_path,
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "Path('source.txt').write_text('destroyed'); "
                "Path('untracked/note.txt').unlink(); "
                "raise SystemExit(7)"
            ),
        ],
    )
    assert result.returncode == 7
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_isolated_timeout_does_not_change_source(tmp_path: Path) -> None:
    (tmp_path / "original").write_text("keep")
    with pytest.raises(subprocess.TimeoutExpired):
        run_isolated(tmp_path, [sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert (tmp_path / "original").read_text() == "keep"


def test_missing_verifier_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    result = verify(tmp_path)
    assert result.evidence == "unknown"
    assert result.exit_code is None
    assert not result.passed


def test_verify_rejects_invalid_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Not a directory"):
        verify(tmp_path / "missing")


def test_timeout_retains_output_and_is_not_a_pass(tmp_path: Path) -> None:
    (tmp_path / "slow.py").write_text("import time\nprint('STARTED', flush=True)\ntime.sleep(10)\n")
    (tmp_path / "Makefile").write_text(f'verify:\n\t@"{sys.executable}" slow.py\n')
    result = verify(tmp_path, timeout=1)
    assert result.evidence == "unknown"
    assert not result.passed
    assert "STARTED" in result.stdout
    assert "timed out" in result.stderr
