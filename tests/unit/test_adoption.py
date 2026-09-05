"""Adoption must preserve conventions, avoid overwrites, and expose incomplete setup."""

import json
import subprocess
from pathlib import Path

import pytest

from ai_ready.adoption import Plan, apply_plan, detect_stack, plan_adoption


def node(root: Path, **extra: object) -> None:
    (root / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "eslint .",
                    "format:check": "prettier --check .",
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                },
                **extra,
            }
        )
    )
    (root / "package-lock.json").write_text("{}")


def test_cdk_detection_is_specific(tmp_path: Path) -> None:
    node(tmp_path)
    (tmp_path / "tsconfig.json").write_text("{}")
    assert detect_stack(tmp_path) == ["node-typescript"]
    (tmp_path / "cdk.json").write_text("{}")
    assert detect_stack(tmp_path) == ["cdk-typescript"]
    plan = plan_adoption(tmp_path)
    assert plan.stack == "cdk-typescript"
    assert "npm run test" in plan.files["Makefile"]
    assert "jest" not in plan.files["Makefile"]


@pytest.mark.parametrize(
    "manager,lock,bootstrap",
    [
        ("pnpm@9.0.0", "pnpm-lock.yaml", "pnpm install --frozen-lockfile"),
        ("yarn@4.0.0", "yarn.lock", "yarn install --immutable"),
        ("yarn@1.22.0", "yarn.lock", "yarn install --frozen-lockfile"),
    ],
)
def test_node_package_manager_is_preserved(
    tmp_path: Path,
    manager: str,
    lock: str,
    bootstrap: str,
) -> None:
    node(tmp_path, packageManager=manager)
    (tmp_path / "package-lock.json").unlink()
    (tmp_path / lock).write_text("")
    plan = plan_adoption(tmp_path)
    assert bootstrap in plan.files["Makefile"]
    assert f"{manager.split('@')[0]} run test" in plan.files["Makefile"]


def test_conflicting_locks_refuse_to_guess(tmp_path: Path) -> None:
    node(tmp_path)
    (tmp_path / "yarn.lock").write_text("")
    with pytest.raises(ValueError, match="Conflicting"):
        plan_adoption(tmp_path)


@pytest.mark.parametrize("package", [[], {"scripts": []}, {"packageManager": "bun@1"}])
def test_invalid_node_configuration_is_rejected(tmp_path: Path, package: object) -> None:
    (tmp_path / "package.json").write_text(json.dumps(package))
    with pytest.raises(ValueError):
        plan_adoption(tmp_path)


def test_missing_commands_do_not_produce_green_verify(tmp_path: Path) -> None:
    node(tmp_path, scripts={})
    (tmp_path / "package-lock.json").unlink()
    plan = plan_adoption(tmp_path)
    assert plan.gaps
    apply_plan(tmp_path, plan)
    result = subprocess.run(["make", "verify"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Adoption incomplete" in result.stdout


def test_python_existing_tools_and_lock_are_reused(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.ruff]\n[tool.mypy]\n[tool.pytest.ini_options]\n[tool.importlinter]\n"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "uv.lock").write_text("")
    plan = plan_adoption(tmp_path)
    assert not plan.gaps
    assert "uv sync --frozen --all-extras" in plan.files["Makefile"]
    assert "uv run --frozen --all-extras mypy src" in plan.files["Makefile"]
    assert "lint-imports" in plan.files["Makefile"]


def test_python_without_tools_records_gaps(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests")
    plan = plan_adoption(tmp_path)
    assert len(plan.gaps) == 4
    assert "adoption-incomplete" in plan.files["Makefile"]


def test_poetry_environment_is_preserved(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
    (tmp_path / "poetry.lock").write_text("")
    assert "poetry run mypy ." in plan_adoption(tmp_path).files["Makefile"]


def test_multiple_stacks_require_selection(tmp_path: Path) -> None:
    node(tmp_path)
    (tmp_path / "pyproject.toml").write_text("")
    with pytest.raises(ValueError, match="Multiple stacks"):
        plan_adoption(tmp_path)
    assert plan_adoption(tmp_path, "python").stack == "python"
    with pytest.raises(ValueError, match="not detected"):
        plan_adoption(tmp_path, "rust")


def test_preview_and_apply_preserve_existing_files(tmp_path: Path) -> None:
    node(tmp_path)
    original = b"verify:\n\t@echo existing\n"
    (tmp_path / "Makefile").write_bytes(original)
    (tmp_path / "AGENTS.md").write_text("My rules")
    plan = plan_adoption(tmp_path)
    assert not (tmp_path / "ADOPTION.md").exists()
    assert plan.diff().startswith("--- /dev/null")
    assert "Makefile" not in plan.files and "AGENTS.md" not in plan.files
    apply_plan(tmp_path, plan)
    assert (tmp_path / "Makefile").read_bytes() == original
    assert (tmp_path / "AGENTS.md").read_text() == "My rules"
    assert not plan_adoption(tmp_path).files


def test_stale_plan_is_rejected_before_any_files_are_created(tmp_path: Path) -> None:
    node(tmp_path)
    plan = plan_adoption(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Concurrent edit")
    with pytest.raises(ValueError, match="stale"):
        apply_plan(tmp_path, plan)
    assert not (tmp_path / "Makefile").exists()


def test_plan_cannot_escape_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        apply_plan(tmp_path, Plan("python", {"../escaped": "bad"}, ()))
    (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        apply_plan(tmp_path, Plan("python", {"link/escaped": "bad"}, ()))


@pytest.mark.parametrize(
    "marker,stack",
    [
        ("main.tf", "terraform"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("pom.xml", "java-maven"),
    ],
)
def test_detected_but_unsupported_stacks_do_not_get_invented_checks(
    tmp_path: Path,
    marker: str,
    stack: str,
) -> None:
    (tmp_path / marker).touch()
    assert detect_stack(tmp_path) == [stack]
    with pytest.raises(ValueError, match="not supported"):
        plan_adoption(tmp_path)


def test_unknown_and_missing_repositories_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No recognized"):
        plan_adoption(tmp_path)
    with pytest.raises(ValueError, match="Not a directory"):
        plan_adoption(tmp_path / "missing")
