#!/usr/bin/env python3
"""
AI-readiness audit for an existing Python repository.

Checks 20 items across the four maturity levels and prints a score
with specific gaps and suggested next steps.

Usage:
    python ai_readiness_audit.py          # audit current directory
    python ai_readiness_audit.py /path    # audit specific repo
"""

import sys
import subprocess
from pathlib import Path


def check(label: str, condition: bool, fix: str) -> tuple[bool, str, str]:
    return condition, label, fix


def run(cmd: str, cwd: Path) -> bool:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, cwd=cwd, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _secret_scanning_enabled(cwd: Path) -> bool:
    """Check GitHub secret scanning via the repo settings API.

    Uses `gh repo view` to get the canonical owner/repo slug, then checks
    `.security_and_analysis.secret_scanning.status` on the repos endpoint.
    Falls back to False if gh CLI is unavailable or the repo is not on GitHub.
    """
    try:
        slug_result = subprocess.run(
            "gh repo view --json nameWithOwner -q .nameWithOwner",
            shell=True, capture_output=True, text=True, cwd=cwd, timeout=10,
        )
        slug = slug_result.stdout.strip()
        if not slug:
            return False
        api_result = subprocess.run(
            f"gh api repos/{slug} --jq '.security_and_analysis.secret_scanning.status'",
            shell=True, capture_output=True, text=True, cwd=cwd, timeout=10,
        )
        return api_result.stdout.strip() == "enabled"
    except Exception:
        return False


def audit(root: Path) -> None:
    results: list[tuple[bool, str, str, str]] = []

    def add(level: str, label: str, passed: bool, fix: str) -> None:
        results.append((passed, level, label, fix))

    # ── Level 1: Runnable ────────────────────────────────────────────────────

    add("L1", "Python version pinned (.python-version or pyproject.toml)",
        (root / ".python-version").exists() or
        (root / "mise.toml").exists() or
        ("requires-python" in (root / "pyproject.toml").read_text()
         if (root / "pyproject.toml").exists() else False),
        "echo '3.12' > .python-version")

    add("L1", "Dependency lockfile present",
        any((root / f).exists() for f in [
            "uv.lock", "poetry.lock", "requirements.txt",
            "requirements-dev.txt", "Pipfile.lock", "pdm.lock"
        ]),
        "uv pip compile pyproject.toml -o requirements-dev.txt")

    add("L1", ".env.example present",
        (root / ".env.example").exists(),
        "cp .env.example .env  # then create .env.example with safe defaults")

    add("L1", "Bootstrap command exists (make bootstrap or scripts/bootstrap)",
        run("make help 2>/dev/null | grep -q bootstrap", root) or
        (root / "scripts" / "bootstrap").exists() or
        (root / "scripts" / "bootstrap.sh").exists(),
        "Add 'bootstrap' target to Makefile — see ADOPT.md Step 2")

    add("L1", "Verification command exists (make verify)",
        run("make help 2>/dev/null | grep -q verify", root),
        "Add 'verify' target to Makefile — see ADOPT.md Step 3")

    # ── Level 2: Verifiable ──────────────────────────────────────────────────

    pyproject_text = (root / "pyproject.toml").read_text() if (root / "pyproject.toml").exists() else ""

    add("L2", "Formatter configured (ruff/black/autopep8)",
        any([
            "tool.ruff" in pyproject_text,
            (root / ".black").exists(),
            run("black --version 2>/dev/null", root),
        ]),
        "uv pip install ruff && add [tool.ruff] to pyproject.toml — see ADOPT.md Step 4")

    add("L2", "Linter configured",
        any([
            "tool.ruff.lint" in pyproject_text,
            (root / ".flake8").exists(),
            (root / "setup.cfg").exists(),
            "tool.pylint" in pyproject_text,
        ]),
        "Add [tool.ruff.lint] section to pyproject.toml — see ADOPT.md Step 4")

    add("L2", "Type checker configured (mypy/pyright)",
        any([
            "tool.mypy" in ((root / "pyproject.toml").read_text()
                            if (root / "pyproject.toml").exists() else ""),
            (root / "pyrightconfig.json").exists(),
            (root / "mypy.ini").exists(),
        ]),
        "Add [tool.mypy] to pyproject.toml — see ADOPT.md Step 5")

    add("L2", "Tests present",
        any((root / d).exists() for d in ["tests", "test", "spec"]),
        "Create tests/ directory with at least one test file")

    add("L2", "CI workflow present",
        (root / ".github" / "workflows").exists() and
        any((root / ".github" / "workflows").glob("*.yml")),
        "Add .github/workflows/ci.yml — copy from ai-ready-repo")

    add("L2", "CI calls same command as local (make verify)",
        any(
            "make verify" in f.read_text()
            for f in (root / ".github" / "workflows").glob("*.yml")
        ) if (root / ".github" / "workflows").exists() else False,
        "Update CI workflow to call: run: make verify")

    add("L2", "No flaky test markers without owners",
        not run(
            "grep -r 'pytest.mark.skip\\|xfail' tests/ 2>/dev/null | grep -v '# owner:'",
            root
        ),
        "Add '# owner: @handle' to every skipped/xfail test or fix them")

    # ── Level 3: Agent-safe ──────────────────────────────────────────────────

    add("L3", "CODEOWNERS present",
        (root / ".github" / "CODEOWNERS").exists() or
        (root / "CODEOWNERS").exists(),
        "Create .github/CODEOWNERS — see template in ai-ready-repo")

    add("L3", "Import boundaries enforced (import-linter or equivalent)",
        "importlinter" in ((root / "pyproject.toml").read_text()
                           if (root / "pyproject.toml").exists() else "") or
        (root / ".importlinter").exists(),
        "uv pip install import-linter && add contracts to pyproject.toml — see ADOPT.md Step 6")

    agent_file = next(
        (root / name for name in ("AGENTS.md", "CLAUDE.md") if (root / name).exists()),
        None,
    )

    add("L3", "Agent instruction file present (AGENTS.md or CLAUDE.md)",
        agent_file is not None,
        "Create AGENTS.md — copy template from ai-ready-repo")

    add("L3", "Agent instruction file is minimal (<100 lines)",
        len(agent_file.read_text().splitlines()) < 100
        if agent_file is not None else False,
        "Trim instruction file — remove rules the tools already enforce")

    add("L3", "ADRs present with Verification sections",
        any(
            "## Verification" in f.read_text()
            for f in (root / "docs" / "adr").glob("*.md")
        ) if (root / "docs" / "adr").exists() else False,
        "Create docs/adr/ and add ADRs with Verification sections — see ADOPT.md Step 8")

    add("L3", "Secret scanning enabled (GitHub secret scanning or equivalent)",
        _secret_scanning_enabled(root) or (root / ".pre-commit-config.yaml").exists(),
        "Enable secret scanning in GitHub Settings → Security")

    # ── Level 4: Measured ────────────────────────────────────────────────────

    add("L4", "Evaluation tasks present",
        (root / "scripts" / "eval_tasks").exists() and
        any((root / "scripts" / "eval_tasks").glob("*.yaml")),
        "Create scripts/eval_tasks/ with representative coding tasks — see ADOPT.md Step 10")

    add("L4", "Daily evaluation workflow scheduled",
        any(
            "schedule" in f.read_text() and "eval" in f.name
            for f in (root / ".github" / "workflows").glob("*.yml")
        ) if (root / ".github" / "workflows").exists() else False,
        "Add .github/workflows/eval-daily.yml — copy from ai-ready-repo")

    # ── Report ───────────────────────────────────────────────────────────────

    levels = {"L1": [], "L2": [], "L3": [], "L4": []}
    for passed, level, label, fix in results:
        levels[level].append((passed, label, fix))

    level_names = {
        "L1": "Level 1 — Runnable",
        "L2": "Level 2 — Verifiable",
        "L3": "Level 3 — Agent-safe",
        "L4": "Level 4 — Measured",
    }

    total_passed = sum(1 for p, _, _, _ in results if p)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  AI-Readiness Audit: {root.name}")
    print(f"  Score: {total_passed}/{total}")
    print(f"{'='*60}\n")

    current_level = 0
    for lk in ["L1", "L2", "L3", "L4"]:
        checks = levels[lk]
        passed = sum(1 for p, _, _ in checks if p)
        total_l = len(checks)
        status = "✓" if passed == total_l else f"{passed}/{total_l}"
        print(f"  {level_names[lk]}: {status}")

        for p, label, fix in checks:
            icon = "  ✓" if p else "  ✗"
            print(f"    {icon}  {label}")
            if not p:
                print(f"         → {fix}")

        if passed == total_l and current_level == list(levels.keys()).index(lk):
            current_level += 1
        print()

    print(f"  Current level: {current_level}")
    if current_level < 4:
        next_level = f"L{current_level + 1}"
        gaps = [(label, fix) for p, label, fix in levels[next_level] if not p]
        if gaps:
            print(f"\n  Next step (to reach {level_names[next_level]}):")
            for label, fix in gaps:
                print(f"    • {label}")
                print(f"      {fix}")
    print()


if __name__ == "__main__":
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    audit(repo_root)
