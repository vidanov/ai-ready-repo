"""Deterministic, additive adoption plans for existing Python and Node projects."""

from __future__ import annotations

import difflib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Plan:
    stack: str
    files: dict[str, str]
    gaps: tuple[str, ...]

    def diff(self) -> str:
        """Render every proposed file as an ordinary unified diff."""
        return "".join(
            "".join(difflib.unified_diff([], body.splitlines(keepends=True), "/dev/null", path))
            for path, body in sorted(self.files.items())
        )


def detect_stack(root: Path) -> list[str]:
    """Prefer specific project markers; tsconfig alone never identifies CDK."""
    found = []
    if any((root / name).is_file() for name in ("pyproject.toml", "setup.py", "setup.cfg")):
        found.append("python")
    elif (root / "requirements.txt").is_file():
        found.append("python")
    if (root / "cdk.json").is_file() and (root / "package.json").is_file():
        found.append("cdk-typescript")
    elif (root / "package.json").is_file():
        found.append("node-typescript")
    if any(root.glob("*.tf")) or any((root / "modules").glob("**/*.tf")):
        found.append("terraform")
    for marker, stack in (("go.mod", "go"), ("Cargo.toml", "rust"), ("pom.xml", "java-maven")):
        if (root / marker).is_file():
            found.append(stack)
    return found


def _node_commands(root: Path) -> tuple[dict[str, str], list[str]]:
    package = json.loads((root / "package.json").read_text())
    if not isinstance(package, dict) or not isinstance(package.get("scripts", {}), dict):
        raise ValueError("package.json must contain an object with a scripts object")
    scripts = package.get("scripts", {})
    lockfiles = {"pnpm": "pnpm-lock.yaml", "yarn": "yarn.lock", "npm": "package-lock.json"}
    managers = [manager for manager, path in lockfiles.items() if (root / path).is_file()]
    declared = str(package.get("packageManager", "")).split("@")[0]
    if len(managers) > 1 or (declared and managers and declared != managers[0]):
        raise ValueError("Conflicting package managers; resolve packageManager and lockfiles first")
    manager = declared or (managers[0] if managers else "npm")
    if manager not in lockfiles:
        raise ValueError(f"Unsupported package manager: {manager}")
    commands = {}
    gaps = []
    if managers:
        commands["bootstrap"] = {
            "npm": "npm ci",
            "pnpm": "pnpm install --frozen-lockfile",
            "yarn": "yarn install --immutable"
            if declared and not str(package["packageManager"]).startswith("yarn@1.")
            else "yarn install --frozen-lockfile",
        }[manager]
    else:
        gaps.append(f"Commit a {manager} lockfile and configure bootstrap.")
    for target, candidates in {
        "format-check": ("format:check", "format-check"),
        "lint": ("lint",),
        "typecheck": ("typecheck", "type-check"),
        "test": ("test",),
    }.items():
        name = next((name for name in candidates if isinstance(scripts.get(name), str)), None)
        if name and scripts[name].strip():
            commands[target] = f"{manager} run {name}"
        else:
            gaps.append(f"Configure a package.json script for {target}.")
    return commands, gaps


def _python_commands(root: Path) -> tuple[dict[str, str], list[str]]:
    path = root / "pyproject.toml"
    config = tomllib.loads(path.read_text()) if path.is_file() else {}
    tools = config.get("tool", {})
    paths = [name for name in ("src", "tests") if (root / name).is_dir()] or ["."]
    scope = " ".join(paths)
    commands = {}
    gaps = []
    # Reuse a locked project environment; don't assume an arbitrary repo has .[dev].
    if (root / "uv.lock").is_file():
        commands["bootstrap"] = "uv sync --frozen --all-extras"
        prefix = "uv run --frozen --all-extras "
    elif (root / "poetry.lock").is_file():
        commands["bootstrap"] = "poetry install"
        prefix = "poetry run "
    else:
        prefix = ""
        gaps.append("Configure a locked Python environment and bootstrap command.")
    if "ruff" in tools:
        commands["format-check"] = prefix + f"ruff format --check {scope}"
        commands["lint"] = prefix + f"ruff check {scope}"
    else:
        gaps.append("Configure Python formatting and lint checks.")
    if "mypy" in tools:
        commands["typecheck"] = prefix + ("mypy src" if "src" in paths else "mypy .")
    else:
        gaps.append("Configure a Python type check.")
    if "pytest" in tools:
        commands["test"] = prefix + "pytest"
    else:
        gaps.append("Configure the project's test command.")
    if "importlinter" in tools:
        commands["import-check"] = prefix + "lint-imports"
    return commands, gaps


def _makefile(commands: dict[str, str], gaps: list[str]) -> str:
    lines = ["# Generated adoption plan. Review before applying.\n.DEFAULT_GOAL := help\n"]
    for target, command in commands.items():
        lines.append(f".PHONY: {target}\n{target}: ## Run {target}\n\t{command}\n")
    checks = [target for target in commands if target != "bootstrap"]
    if gaps:
        lines.append(
            ".PHONY: adoption-incomplete\nadoption-incomplete:\n"
            '\t@echo "Adoption incomplete: resolve ADOPTION.md before claiming verification."\n'
            "\t@exit 1\n"
        )
        checks.append("adoption-incomplete")
    lines.append(f".PHONY: verify\nverify: {' '.join(checks)} ## Run configured checks\n")
    help_lines = " ".join(f"'{target}'" for target in [*commands, "verify"])
    lines.append(f".PHONY: help\nhelp:\n\t@printf '%s\\n' {help_lines}\n")
    return "\n".join(lines)


def plan_adoption(root: Path, stack: str | None = None) -> Plan:
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    stacks = detect_stack(root)
    if not stacks:
        raise ValueError("No recognized project detected")
    if stack is None and len(stacks) != 1:
        raise ValueError(f"Multiple stacks detected ({', '.join(stacks)}); select --stack")
    selected = stack or stacks[0]
    if selected not in stacks:
        raise ValueError(f"Selected stack {selected} was not detected")
    if selected not in {"python", "node-typescript", "cdk-typescript"}:
        raise ValueError(f"{selected} is detected but automated adoption is not supported yet")
    commands, gaps = _python_commands(root) if selected == "python" else _node_commands(root)
    files = {}
    if not (root / "Makefile").exists():
        files["Makefile"] = _makefile(commands, gaps)
    else:
        gaps.append("Existing Makefile preserved: integrate the proposed commands manually.")
    if not (root / "AGENTS.md").exists():
        files["AGENTS.md"] = (
            f"# Agent guidance\n\nStack: {selected}\n\n"
            "Read ADOPTION.md for remaining setup work. Run `make verify` to check changes.\n"
            "Record project-specific constraints here after reviewing the generated plan.\n"
            "Report commands, exit codes, changed files, and unverified behavior.\n"
        )
    if not (root / "ADOPTION.md").exists():
        files["ADOPTION.md"] = (
            "# Adoption plan\n\nGenerated deterministically from existing project configuration.\n"
            "No commands have been executed. Review these files before committing.\n\n"
            "## Detected commands\n\n"
            + "".join(f"- {name}: `{command}`\n" for name, command in commands.items())
            + "\n## Remaining work\n\n"
            + "".join(f"- {gap}\n" for gap in gaps)
            + "- Run the checks and connect the verified entry point to CI.\n"
            "- Define project-specific boundaries and drills that reject violations.\n"
        )
    return Plan(selected, files, tuple(gaps))


def apply_plan(root: Path, plan: Plan) -> None:
    """Create only new files; reject stale plans and paths outside the destination."""
    for relative in plan.files:
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Plan path escapes destination: {relative}")
        if path.exists() or path.is_symlink():
            raise ValueError(f"Plan is stale; refusing to overwrite {relative}")
    for relative, content in plan.files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            stream.write(content)
