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


@pytest.mark.parametrize("staged", [False, True], ids=["unstaged", "staged"])
def test_eval_isolation_preserves_verdict_across_real_git_states(
    tmp_path: Path, staged: bool
) -> None:
    """Exercise the real diff reader, with a dirty unisolated negative control."""
    import json
    import os
    import shutil

    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, env=env, check=True, capture_output=True, text=True
        ).stdout

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(Path(__file__).parents[2] / "scripts/run_evals.py", scripts / "run_evals.py")
    github = tmp_path / ".github"
    github.mkdir()
    (github / "CODEOWNERS").write_text("/protected.txt @example\n")
    protected = tmp_path / "protected.txt"
    protected.write_text("original\n")
    (tmp_path / "task.yaml").write_text(
        'description: isolation probe\nverification: "true"\n'
        'expected_exit_code: 0\norigin: birth\noracle_question: "Does this run?"\n'
    )
    (tmp_path / "probe.py").write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, 'scripts')\nimport run_evals\n"
        "r = run_evals.run_task(Path('task.yaml'))\n"
        "print(json.dumps({k: r[k] for k in "
        "('passed', 'verdict', 'protected_touched', 'diff_lines')}))\n"
    )
    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Isolation test",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "Fixture baseline",
    )
    command = [sys.executable, "-B", "probe.py"]
    clean = run_isolated(tmp_path, command)
    assert clean.returncode == 0, clean.stderr
    expected = json.loads(clean.stdout)
    assert expected["passed"] is True
    assert expected["protected_touched"] == []
    assert expected["diff_lines"] == 0

    protected.write_text("deliberately dirty\n")
    if staged:
        git("add", "protected.txt")
    before = git("status", "--porcelain")
    assert before.strip()

    # Prove that this manufactured state actually triggers the original coupling.
    direct = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert direct.returncode == 0, direct.stderr
    coupled = json.loads(direct.stdout)
    assert coupled["passed"] is False
    assert coupled["protected_touched"] == ["protected.txt"]
    assert coupled["diff_lines"] > 0

    # The direct (unisolated) run may create __pycache__ inside tmp_path/scripts/.
    # Remove it so the git-status comparison below is not polluted by an untracked
    # directory that did not exist when `before` was captured.
    import shutil as _shutil

    for _pycache in tmp_path.rglob("__pycache__"):
        _shutil.rmtree(_pycache, ignore_errors=True)

    isolated = run_isolated(tmp_path, command)
    assert isolated.returncode == 0, isolated.stderr
    assert json.loads(isolated.stdout) == expected
    assert protected.read_text() == "deliberately dirty\n"
    assert git("status", "--porcelain") == before
