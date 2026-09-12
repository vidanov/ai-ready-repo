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
    def score_bounds(self) -> tuple[int, int]:
        # The score alone treats `unknown` (could-not-establish) exactly like
        # `missing` (known-absent): both are simply not-configured, so a reader
        # quoting one number cannot see how much of the gap is real absence
        # versus unestablished. That is the defect manu (1f916 #5003) and
        # lattice-sentinel (#4533) named: a breakdown beside a single fraction
        # still lets the fraction get quoted alone. So the honest aggregate is
        # a pair, not a point:
        #   pessimistic = configured only (every unknown resolves against you)
        #   optimistic  = configured + unknown (every unknown resolves for you)
        # When they differ, the spread IS the headline: it says how much of the
        # score is a policy choice about the unknowns, not a measured fact.
        configured = self.score
        unknown = sum(f.evidence == "unknown" for f in self.findings)
        return (configured, configured + unknown)

    @property
    def breakdown(self) -> dict[str, int]:
        # configured / missing / unknown kept apart: an unknown finding is
        # "could not establish", not "known absent". The score counts only
        # configured, so without this an unknown is indistinguishable from a
        # missing one in the denominator (1f916 #4517 scaffold, #4454 zola:
        # a blank is not a wrong answer; do not fold the missing edge into the
        # aggregate).
        counts = {"configured": 0, "missing": 0, "unknown": 0}
        for finding in self.findings:
            counts[finding.evidence] = counts.get(finding.evidence, 0) + 1
        return counts

    @property
    def level(self) -> int:
        level = 0
        for candidate in range(1, 5):
            if any(f.evidence != "configured" for f in self.findings if f.level == candidate):
                break
            level = candidate
        return level

    def to_dict(self) -> dict[str, object]:
        low, high = self.score_bounds
        return {
            "score": self.score,
            "score_bounds": {"pessimistic": low, "optimistic": high},
            "total": len(self.findings),
            "breakdown": self.breakdown,
            "level": self.level,
            "scope": "configuration inventory; no project commands executed",
            "findings": [asdict(f) for f in self.findings],
        }

    def render(self) -> str:
        counts = self.breakdown
        total = len(self.findings)
        low, high = self.score_bounds
        # When there are unknowns the score is a range, not a point: quoting a
        # single number would hide the policy choice about how the unknowns
        # resolve. Show the spread in the headline (not just the breakdown), so
        # the aggregate itself distinguishes unknown from missing (manu, #5003).
        if low == high:
            score_line = f"Configuration score: {low}/{total}\n"
        else:
            score_line = (
                f"Configuration score: {low}-{high}/{total} "
                f"(pessimistic {low}, optimistic {high}; the {high - low}-point "
                "spread is unknown, not measured absence)\n"
            )
        return (
            score_line + f"  configured {counts['configured']}, "
            f"missing {counts['missing']}, unknown {counts['unknown']} "
            "(unknown is not-established, not known-absent)\n"
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

    def add_marker(level: int, name: str, matched: bool, detail: str) -> None:
        # For checks that scan for a KNOWN SET of tool markers, a negative
        # result is "my markers did not match", not "the tool is absent from the
        # world" (ox-alpha-big-pickle, 1f916 #4533: absent is a self-attributing
        # claim; a scanner that never runs reports the same clean absence as one
        # that runs faithfully). These emit `unknown`, not `missing`, when
        # negative: the audit cannot establish that no formatter/linter/type
        # checker/CI reference/boundary contract is configured, only that it did
        # not recognize a marker it knows. `missing` stays for checks whose slot
        # is a named file or Makefile target on disk, where absence is a
        # checkable world-fact. See backlog #039.
        checks.append(Finding(name, level, "configured" if matched else "unknown", detail))

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
    add_marker(
        2,
        "Formatter",
        "[tool.ruff]" in pyproject
        or "[tool.black]" in pyproject
        or bool(re.search(r"^format-check:", makefile, re.M)),
        "Configuration only.",
    )
    add_marker(
        2,
        "Linter",
        "[tool.ruff.lint]" in pyproject or bool(re.search(r"^lint:", makefile, re.M)),
        "Configuration only.",
    )
    add_marker(
        2,
        "Types",
        "[tool.mypy]" in pyproject
        or (root / "tsconfig.json").is_file()
        or (root / "pyrightconfig.json").is_file(),
        "Configuration only.",
    )
    add(2, "Test files", bool(tests), f"Found {len(tests)} matching test files; not executed.")
    add(2, "CI workflow", bool(workflows), ".github/workflows")
    add_marker(
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
    add_marker(
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
