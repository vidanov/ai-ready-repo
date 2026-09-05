"""CI coverage follows actual run steps and the local prerequisite graph."""

from pathlib import Path

import pytest

from scripts import drill_ci_coverage


def test_prerequisites_are_transitive_and_cycles_terminate() -> None:
    assert drill_ci_coverage.expand_prerequisites(
        {"verify"},
        "verify: fast test\nfast: lint types\nloop: loop\n",
    ) == {"verify", "fast", "test", "lint", "types"}
    assert drill_ci_coverage.expand_prerequisites({"loop"}, "loop: loop\n") == {"loop"}


def test_workflow_comments_are_not_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("verify: lint test\n")
    (tmp_path / "ci.yaml").write_text(
        "# make absent\njobs:\n  verify:\n    steps:\n"
        "      - name: make pretend\n        run: make verify\n"
    )
    monkeypatch.setattr(drill_ci_coverage, "MAKEFILE", makefile)
    monkeypatch.setattr(drill_ci_coverage, "CI_DIR", tmp_path)
    assert drill_ci_coverage.get_ci_referenced_targets() == {"verify", "lint", "test"}
