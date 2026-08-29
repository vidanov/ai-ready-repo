#!/usr/bin/env python3
"""
Agent evaluation runner.

Runs representative coding tasks against this repository and reports
task success rate, runtime, and any regressions from the baseline.

Measures five dimensions per task (inspired by Captain's eval harness):
  - verify_pass: did the verification command exit as expected?
  - tests_disabled: did the agent skip/xfail tests to make them pass?
  - protected_touched: did the agent modify CODEOWNERS-protected paths?
  - diff_lines: total insertions + deletions (scope creep signal)
  - done_condition: did the task's specific done-condition pass?

Usage:
    python scripts/run_evals.py                  # run all tasks
    python scripts/run_evals.py --task add-field # run one task
    python scripts/run_evals.py --baseline       # update baseline

Tasks are defined in scripts/eval_tasks/. Each task is a YAML file with:
  - description: what the agent should do
  - verification: command to verify the result
  - expected_exit_code: 0 for success
  - done_condition: (optional) shell command that exits 0 if task completed
  - protected_paths: (optional) list of paths the agent must not touch
  - max_diff_lines: (optional) diff size cap

Exit code:
  0 — all tasks passed and success rate >= baseline
  1 — tasks failed or success rate regressed
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

TASKS_DIR = Path(__file__).parent / "eval_tasks"
BASELINE_FILE = Path(__file__).parent / "eval_baseline.json"
CODEOWNERS_FILE = Path(__file__).parent.parent / ".github" / "CODEOWNERS"

# Patterns that indicate tests were disabled rather than fixed
SKIP_PATTERNS = [
    r"@pytest\.mark\.skip",
    r"@pytest\.mark\.xfail",
    r"pytest\.skip\(",
    r"@unittest\.skip",
    r"@unittest\.expectedFailure",
    r"\bxit\(",          # Jasmine/Jest
    r"\bxdescribe\(",   # Jasmine/Jest
    r"\.skip\(",        # Mocha/Vitest
]
SKIP_RE = re.compile("|".join(SKIP_PATTERNS))


def load_baseline() -> dict[str, float]:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {}


def save_baseline(results: dict[str, float]) -> None:
    BASELINE_FILE.write_text(json.dumps(results, indent=2))
    print(f"Baseline saved to {BASELINE_FILE}")


def parse_codeowners() -> list[str]:
    """Extract protected path prefixes from CODEOWNERS."""
    if not CODEOWNERS_FILE.exists():
        return []
    paths = []
    for line in CODEOWNERS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # First token is the path pattern, rest are owners
        parts = line.split()
        if parts:
            paths.append(parts[0].lstrip("/"))
    return paths


def get_diff_stats() -> tuple[int, list[str]]:
    """Return (total_diff_lines, changed_files) from git diff against HEAD."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0, []

    lines = result.stdout.strip().splitlines()
    if not lines:
        return 0, []

    # Parse changed files
    changed = []
    for line in lines[:-1]:  # last line is the summary
        parts = line.strip().split("|")
        if len(parts) >= 1:
            fname = parts[0].strip()
            if fname:
                changed.append(fname)

    # Parse summary line: "X files changed, Y insertions(+), Z deletions(-)"
    summary = lines[-1] if lines else ""
    total = 0
    for match in re.finditer(r"(\d+) insertion", summary):
        total += int(match.group(1))
    for match in re.finditer(r"(\d+) deletion", summary):
        total += int(match.group(1))

    return total, changed


def count_tests_disabled_in_diff() -> int:
    """Count lines in git diff that add test-skip patterns."""
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0

    count = 0
    for line in result.stdout.splitlines():
        # Only count added lines (starting with +, not ++)
        if line.startswith("+") and not line.startswith("+++"):
            if SKIP_RE.search(line):
                count += 1
    return count


def check_protected_paths(changed_files: list[str]) -> list[str]:
    """Return changed files that match CODEOWNERS-protected paths."""
    protected_prefixes = parse_codeowners()
    if not protected_prefixes:
        return []

    touched = []
    for f in changed_files:
        for prefix in protected_prefixes:
            # Handle glob patterns: strip trailing wildcards for prefix match
            clean = prefix.rstrip("*").rstrip("/")
            if f.startswith(clean):
                touched.append(f)
                break
    return touched


def run_task(task_path: Path) -> dict[str, object]:
    import yaml  # optional dep — only needed when running evals

    task = yaml.safe_load(task_path.read_text())
    start = time.monotonic()

    # Run primary verification
    result = subprocess.run(
        task["verification"],
        shell=True,
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - start
    verify_pass = result.returncode == task.get("expected_exit_code", 0)

    # Run done_condition if specified
    done_ok = True
    if "done_condition" in task:
        done_result = subprocess.run(
            task["done_condition"],
            shell=True,
            capture_output=True,
            text=True,
        )
        done_ok = done_result.returncode == 0

    # Measure diff and scope
    diff_lines, changed_files = get_diff_stats()
    tests_disabled = count_tests_disabled_in_diff()
    protected_touched = check_protected_paths(changed_files)

    # Check constraints
    max_diff = task.get("max_diff_lines")
    diff_ok = diff_lines <= max_diff if max_diff is not None else True

    task_protected = task.get("protected_paths", [])
    extra_protected = []
    if task_protected:
        for f in changed_files:
            for p in task_protected:
                if f.startswith(p.lstrip("/")):
                    extra_protected.append(f)

    # A task passes only if all dimensions are clean
    passed = (
        verify_pass
        and done_ok
        and tests_disabled == 0
        and not protected_touched
        and not extra_protected
        and diff_ok
    )

    return {
        "task": task_path.stem,
        "passed": passed,
        "verify_pass": verify_pass,
        "done_condition_ok": done_ok,
        "tests_disabled": tests_disabled,
        "protected_touched": [str(p) for p in protected_touched],
        "diff_lines": diff_lines,
        "changed_files": changed_files,
        "elapsed": round(elapsed, 2),
        "stdout": result.stdout[:500],
        "stderr": result.stderr[:500],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent evaluation tasks")
    parser.add_argument("--task", help="Run a single task by name")
    parser.add_argument("--baseline", action="store_true", help="Update baseline")
    args = parser.parse_args()

    if not TASKS_DIR.exists():
        print(f"No eval tasks found at {TASKS_DIR}/")
        print("Add YAML task files to get started.")
        return 0

    task_files = sorted(TASKS_DIR.glob("*.yaml"))
    if args.task:
        task_files = [t for t in task_files if t.stem == args.task]

    if not task_files:
        print("No matching tasks found.")
        return 1

    results = [run_task(t) for t in task_files]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    rate = passed / total if total else 0.0

    print(f"\nEval results: {passed}/{total} passed ({rate:.0%})\n")
    for r in results:
        icon = "✓" if r["passed"] else "✗"
        flags = []
        if r["tests_disabled"]:
            flags.append(f"skip:{r['tests_disabled']}")
        if r["protected_touched"]:
            flags.append(f"protected:{len(r['protected_touched'])}")
        if r["diff_lines"] > 0:
            flags.append(f"diff:{r['diff_lines']}")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {icon} {r['task']} ({r['elapsed']}s){flag_str}")

    baseline = load_baseline()
    prior_rate = baseline.get("success_rate", 0.0)

    if args.baseline:
        save_baseline({"success_rate": rate, "tasks": total})
        return 0

    if rate < prior_rate - 0.05:  # 5% regression threshold
        print(f"\n✗ Regression: {rate:.0%} < baseline {prior_rate:.0%}")
        return 1

    print(f"\n✓ Success rate {rate:.0%} (baseline {prior_rate:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
