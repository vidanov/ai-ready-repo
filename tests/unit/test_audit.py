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


def test_marker_set_checks_are_unknown_not_missing_when_no_marker(tmp_path: Path) -> None:
    # A check that greps a known set of tool markers cannot establish world
    # absence on a negative -- it only knows its markers did not match. Those
    # emit `unknown`, not `missing` (ox-alpha-big-pickle, 1f916 #4533; backlog
    # #039). File/target-on-disk checks keep `missing`, where absence is real.
    findings = {f.name: f.evidence for f in audit(tmp_path).findings}
    for name in (
        "Formatter",
        "Linter",
        "Types",
        "CI verification entry point",
        "Import boundaries",
    ):
        assert findings[name] == "unknown", name
    for name in ("Runtime pin", "Dependency lock", "Test files"):
        assert findings[name] == "missing", name


def test_breakdown_separates_unknown_from_missing(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.12"')
    report = audit(tmp_path)
    counts = report.breakdown
    # unknown (could-not-establish) and missing (known-absent) are distinct
    # buckets, not folded together; the score counts only configured.
    assert counts["unknown"] >= 1
    assert counts["missing"] >= 1
    assert sum(counts.values()) == len(report.findings)
    assert counts["configured"] == report.score
    assert "unknown" in report.render()


def test_score_bounds_diverge_by_the_unknown_count(tmp_path: Path) -> None:
    # The aggregate must distinguish unknown from missing, not just the
    # breakdown (manu, 1f916 #5003): pessimistic counts only configured,
    # optimistic adds the unknowns, and the spread is exactly the unknown count.
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.12"')
    report = audit(tmp_path)
    low, high = report.score_bounds
    counts = report.breakdown
    assert low == report.score  # pessimistic == score (backward compatible)
    assert high - low == counts["unknown"]  # spread is exactly the unknowns
    assert high > low  # this repo has unknowns, so the score is a range


def test_score_bounds_collapse_when_no_unknowns() -> None:
    # A real audit always carries at least one unknown (Agent performance
    # measurements is unconditionally unknown), so the score is always a range
    # in practice -- the audit can never quote a single precise number, which is
    # the honest outcome. The collapse-to-a-point path is still exercised here
    # with synthetic findings, proving render prints a point (not a range) when
    # unknown == 0.
    from ai_ready.audit import Finding, Report

    report = Report(
        (
            Finding("A", 1, "configured", ""),
            Finding("B", 1, "missing", ""),
        )
    )
    low, high = report.score_bounds
    assert report.breakdown["unknown"] == 0
    assert low == high == 1
    assert "1/2" in report.render()  # a point, not a range
    assert "spread is unknown" not in report.render()


def test_real_audit_score_is_always_a_range(tmp_path: Path) -> None:
    # Because Agent performance is unconditionally unknown, even a fully
    # configured repo's score is a pair, not a point: the audit cannot claim a
    # single measured number while it holds something it could not establish.
    for path, body in {
        ".python-version": "3.14",
        "uv.lock": "",
        ".env.example": "",
        "Makefile": "bootstrap:\nverify:\nformat-check:\nlint:\n",
        "pyproject.toml": "[tool.ruff]\n[tool.ruff.lint]\n[tool.mypy]\n[tool.importlinter]\n",
        "tests/test_example.py": "def test_one(): pass\n",
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
    low, high = report.score_bounds
    assert report.breakdown["unknown"] >= 1
    assert high > low


def test_render_shows_the_range_when_unknowns_exist(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.12"')
    rendered = audit(tmp_path).render()
    low, high = audit(tmp_path).score_bounds
    assert f"{low}-{high}/" in rendered
    assert "spread is unknown, not measured absence" in rendered
    # to_dict carries both bounds so a downstream reader can treat them apart
    bounds = audit(tmp_path).to_dict()["score_bounds"]
    assert bounds == {"pessimistic": low, "optimistic": high}


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
