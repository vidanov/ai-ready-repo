"""An added verification check must not disappear from the evaluated population."""

from pathlib import Path

import pytest

from scripts.check_population import main


def fixture(root: Path) -> Path:
    (root / "Makefile").write_text("verify: lint\nlint:\n")
    tasks = root / "scripts/eval_tasks"
    tasks.mkdir(parents=True)
    task = tasks / "checks.yaml"
    task.write_text('verification: "make verify"\ncovers: [lint]\n')
    return task


def test_added_surface_member_without_fixture_fails_then_recovers(tmp_path: Path) -> None:
    task = fixture(tmp_path)
    assert main(tmp_path) == 0
    (tmp_path / "Makefile").write_text("verify: lint new-check\nlint:\nnew-check:\n")
    assert main(tmp_path) == 1
    task.write_text('verification: "make verify"\ncovers: [lint, new-check]\n')
    assert main(tmp_path) == 0


def test_claim_must_be_reached_by_its_command(tmp_path: Path) -> None:
    task = fixture(tmp_path)
    (tmp_path / "Makefile").write_text("verify: lint\nlint:\nnoop:\n")
    task.write_text('verification: "make noop"\ncovers: [lint]\n')
    assert main(tmp_path) == 3


@pytest.mark.parametrize("body", ["[]", "covers: lint", "covers: [42]", "covers: [lint]", "["])
def test_invalid_task_never_passes(tmp_path: Path, body: str) -> None:
    fixture(tmp_path).write_text(body)
    assert main(tmp_path) == 3


def test_missing_population_and_tasks_never_pass(tmp_path: Path) -> None:
    assert main(tmp_path) == 3
    task = fixture(tmp_path)
    task.unlink()
    assert main(tmp_path) == 3


def test_transitive_check_requires_coverage_even_without_phony(tmp_path: Path) -> None:
    fixture(tmp_path)
    (tmp_path / "Makefile").write_text("verify: lint\nlint: nested\nnested:\n")
    assert main(tmp_path) == 1


def test_unknown_prerequisite_never_passes(tmp_path: Path) -> None:
    fixture(tmp_path)
    (tmp_path / "Makefile").write_text("verify: $(CHECKS)\n")
    assert main(tmp_path) == 3
