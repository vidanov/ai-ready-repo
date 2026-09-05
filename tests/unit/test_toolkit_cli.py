"""Public commands expose a preview and machine-readable evidence."""

import json
from pathlib import Path

import pytest

from ai_ready.cli import main


def test_audit_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(tmp_path), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["total"] == 20
    assert "no project commands executed" in result["scope"]
    assert main(["audit", str(tmp_path)]) == 0
    assert "Configuration score" in capsys.readouterr().out


def test_adoption_defaults_to_preview(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    assert main(["adopt", str(tmp_path)]) == 0
    assert not (tmp_path / "Makefile").exists()
    assert "Preview only" in capsys.readouterr().out
    assert main(["adopt", str(tmp_path), "--apply"]) == 0
    assert (tmp_path / "Makefile").exists()
    assert main(["adopt", str(tmp_path), "--detect"]) == 0
    assert "Detected: python" in capsys.readouterr().out


def test_errors_are_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["adopt", str(tmp_path)]) == 2
    assert main(["audit", str(tmp_path / "missing")]) == 2
    assert "Not a directory" in capsys.readouterr().err
    (tmp_path / "package.json").write_text("invalid json")
    assert main(["adopt", str(tmp_path)]) == 2


def test_verify_preserves_output_and_exit_status(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "Makefile").write_text("verify:\n\t@echo CHECKED\n")
    assert main(["verify", str(tmp_path), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["evidence"] == "executed"
    assert result["passed"] and result["stdout"] == "CHECKED\n"
    (tmp_path / "Makefile").write_text("verify:\n\t@echo REJECTED\n\t@exit 1\n")
    assert main(["verify", str(tmp_path)]) == 1
    assert "REJECTED" in capsys.readouterr().out
    assert main(["verify", str(tmp_path), "--timeout", "0"]) == 2
