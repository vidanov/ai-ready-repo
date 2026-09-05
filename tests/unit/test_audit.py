"""Inventory cannot claim runtime evidence from the presence of a file."""

from pathlib import Path

import pytest

from ai_ready.audit import audit


def test_empty_directories_and_generic_hook_config_are_not_evidence(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.12"')
    findings = {f.name: f for f in audit(tmp_path).findings}
    assert findings["Test files"].evidence == "missing"
    assert findings["Secret scanner"].evidence == "unknown"
    assert findings["Runtime pin"].evidence == "missing"
    assert findings["Agent performance measurements"].evidence == "unknown"


def test_audit_never_executes_project_makefile(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("$(shell touch EXECUTED)\nverify:\n\ttrue\n")
    report = audit(tmp_path)
    assert not (tmp_path / "EXECUTED").exists()
    assert "no project commands executed" in str(report.to_dict())
    assert "does not mean executed" in report.render()
    assert report.level == 0


def test_configuration_and_skipped_tests_keep_their_limits(tmp_path: Path) -> None:
    for path, body in {
        ".python-version": "3.14",
        "uv.lock": "",
        ".env.example": "",
        "Makefile": "bootstrap:\nverify:\nformat-check:\nlint:\n",
        "pyproject.toml": "[tool.ruff]\n[tool.ruff.lint]\n[tool.mypy]\n[tool.importlinter]\n",
        "tests/test_example.py": "@pytest.mark.skip\ndef test_one(): pass\n",
        ".github/workflows/ci.yaml": "run: make verify\nscanner: gitleaks\n",
        ".github/CODEOWNERS": "* @owner",
        "AGENTS.md": "Read the rules",
        "docs/adr/decision.md": "## Verification\n",
        "scripts/eval_tasks/check.yaml": "verification: true",
    }.items():
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body)
    report = audit(tmp_path)
    assert report.score == 18
    assert report.level == 1
    assert report.to_dict()["total"] == 20
    assert any(
        f.name == "Skipped test ownership" and f.evidence == "unknown" for f in report.findings
    )
    (tmp_path / "tests/test_example.py").write_text("def test_one(): pass\n")
    assert audit(tmp_path).level == 3


def test_invalid_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Not a directory"):
        audit(tmp_path / "missing")


def test_skip_example_in_a_string_is_not_a_skipped_test(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    path = tmp_path / "tests/test_example.py"
    path.write_text('def test_example():\n    text = "pytest.mark.skip"\n')
    finding = next(f for f in audit(tmp_path).findings if f.name == "Skipped test ownership")
    assert finding.evidence == "configured"
    path.write_text("def invalid syntax")
    finding = next(f for f in audit(tmp_path).findings if f.name == "Skipped test ownership")
    assert finding.evidence == "unknown"


@pytest.mark.parametrize(
    "relative", ["src/order.test.ts", "packages/ui/src/view.spec.tsx", "pkg/test_order.py"]
)
def test_colocated_tests_are_discovered(tmp_path: Path, relative: str) -> None:
    test = tmp_path / relative
    test.parent.mkdir(parents=True)
    test.write_text("")
    finding = next(f for f in audit(tmp_path).findings if f.name == "Test files")
    assert finding.evidence == "configured"


def test_dependency_generated_and_symlinked_tests_are_excluded(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    for directory in ("node_modules/pkg", ".venv/lib", "dist", ".git"):
        test = root / directory / "test_example.py"
        test.parent.mkdir(parents=True)
        test.write_text("")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test_example.py").write_text("")
    (root / "tests").symlink_to(outside, target_is_directory=True)
    (root / "test_link.py").symlink_to(outside / "test_example.py")
    finding = next(f for f in audit(root).findings if f.name == "Test files")
    assert finding.evidence == "missing"
