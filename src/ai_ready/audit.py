"""Read-only inventory: configuration is evidence of setup, not of correctness."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    name: str
    level: int
    evidence: str
    detail: str


@dataclass(frozen=True)
class Report:
    findings: tuple[Finding, ...]

    @property
    def score(self) -> int:
        return sum(f.evidence == "configured" for f in self.findings)

    @property
    def level(self) -> int:
        level = 0
        for candidate in range(1, 5):
            if any(f.evidence != "configured" for f in self.findings if f.level == candidate):
                break
            level = candidate
        return level

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "total": len(self.findings),
            "level": self.level,
            "scope": "configuration inventory; no project commands executed",
            "findings": [asdict(f) for f in self.findings],
        }

    def render(self) -> str:
        return (
            f"Configuration score: {self.score}/{len(self.findings)}\n"
            f"Configuration level: {self.level}\n"
            "No project commands executed. Configured does not mean executed or demonstrated.\n\n"
            + "".join(f"[{f.evidence}] L{f.level} {f.name}: {f.detail}\n" for f in self.findings)
        )


def audit(root: Path) -> Report:
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    def read(path: str) -> str:
        file = root / path
        return file.read_text() if file.is_file() else ""

    pyproject = read("pyproject.toml")
    makefile = read("Makefile")
    workflows = "\n".join(
        path.read_text()
        for suffix in ("*.yml", "*.yaml")
        for path in sorted((root / ".github/workflows").glob(suffix))
    )
    precommit = read(".pre-commit-config.yaml")
    agent = read("AGENTS.md") or read("CLAUDE.md")
    tests: list[Path] = []
    excluded = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        ".nuxt",
        "vendor",
    }
    for directory, subdirectories, filenames in os.walk(root, followlinks=False):
        subdirectories[:] = sorted(name for name in subdirectories if name not in excluded)
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if (
                not path.is_symlink()
                and path.is_file()
                and re.search(r"(^test_.+\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$)", filename)
            ):
                tests.append(path)
    checks: list[Finding] = []

    def add(level: int, name: str, configured: bool, detail: str) -> None:
        checks.append(Finding(name, level, "configured" if configured else "missing", detail))

    add(
        1,
        "Runtime pin",
        any(
            (root / p).is_file()
            for p in (".python-version", ".node-version", ".nvmrc", "mise.toml")
        ),
        "Inspect the runtime version file; a minimum version is not a pin.",
    )
    add(
        1,
        "Dependency lock",
        any(
            (root / p).is_file()
            for p in (
                "uv.lock",
                "poetry.lock",
                "Pipfile.lock",
                "pdm.lock",
                "package-lock.json",
                "pnpm-lock.yaml",
                "yarn.lock",
                "Cargo.lock",
            )
        ),
        "Lockfile presence; reproducible installation has not been run.",
    )
    add(1, "Environment example", (root / ".env.example").is_file(), ".env.example")
    add(1, "Bootstrap entry point", bool(re.search(r"^bootstrap:", makefile, re.M)), "Makefile")
    add(1, "Verification entry point", bool(re.search(r"^verify:", makefile, re.M)), "Makefile")
    add(
        2,
        "Formatter",
        "[tool.ruff]" in pyproject
        or "[tool.black]" in pyproject
        or bool(re.search(r"^format-check:", makefile, re.M)),
        "Configuration only.",
    )
    add(
        2,
        "Linter",
        "[tool.ruff.lint]" in pyproject or bool(re.search(r"^lint:", makefile, re.M)),
        "Configuration only.",
    )
    add(
        2,
        "Types",
        "[tool.mypy]" in pyproject
        or (root / "tsconfig.json").is_file()
        or (root / "pyrightconfig.json").is_file(),
        "Configuration only.",
    )
    add(2, "Test files", bool(tests), f"Found {len(tests)} matching test files; not executed.")
    add(2, "CI workflow", bool(workflows), ".github/workflows")
    add(
        2,
        "CI verification entry point",
        bool(re.search(r"make\s+verify(?:\s|$)", workflows)),
        "Text reference only; workflow execution and branch protection are unknown.",
    )
    skipped = False
    for path in tests:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            skipped = True  # Invalid syntax cannot establish absence of skips.
            continue
        skipped |= any(
            isinstance(node, ast.Attribute)
            and node.attr in {"skip", "skipif", "xfail"}
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "mark"
            for node in ast.walk(tree)
        )
    checks.append(
        Finding(
            "Skipped test ownership",
            2,
            "unknown" if skipped else ("configured" if tests else "unknown"),
            "Review skipped tests individually."
            if skipped
            else "No Python skip markers found; this is a static scan.",
        )
    )
    add(
        3,
        "Code owners",
        bool(read(".github/CODEOWNERS") or read("CODEOWNERS")),
        "Owner declarations only; required reviews are not verified.",
    )
    add(
        3,
        "Import boundaries",
        "[tool.importlinter]" in pyproject or (root / ".importlinter").is_file(),
        "Configured contracts; no violation planted.",
    )
    add(3, "Agent guidance", bool(agent), "AGENTS.md or CLAUDE.md")
    add(
        3,
        "Concise guidance",
        bool(agent) and len(agent.splitlines()) < 100,
        "Under 100 lines; instruction quality is not measured.",
    )
    add(
        3,
        "Verifiable decisions",
        any("## Verification" in p.read_text() for p in (root / "docs/adr").glob("*.md")),
        "ADR verification section present.",
    )
    scanner = bool(re.search(r"\b(gitleaks|detect-secrets|trufflehog)\b", workflows + precommit))
    checks.append(
        Finding(
            "Secret scanner",
            3,
            "configured" if scanner else "unknown",
            "Scanner reference found; execution unverified."
            if scanner
            else "No recognized scanner reference; hosted settings were not queried.",
        )
    )
    add(
        4,
        "Verification regression tasks",
        any((root / "scripts/eval_tasks").glob("*.yaml")),
        "These verify code; they do not measure agent performance.",
    )
    checks.append(
        Finding(
            "Agent performance measurements",
            4,
            "unknown",
            "Requires comparable recorded agent runs; a schedule is not evidence.",
        )
    )
    return Report(tuple(checks))
