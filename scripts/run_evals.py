#!/usr/bin/env python3
"""
Agent evaluation runner.

Runs representative coding tasks against this repository and reports
task success rate, runtime, and any regressions from the baseline.

Measures seven dimensions per task:
  - verify_pass: did the verification command exit as expected?
  - reason_match: did the output contain the expected_reason string?
  - done_condition: did the task's specific done-condition pass?
  - tests_disabled: did the agent skip/xfail tests to make them pass?
  - protected_touched: did the agent modify CODEOWNERS-protected paths?
  - diff_lines: total insertions + deletions (scope creep signal)
  - origin: where the task came from (birth/stranger/second-incident/live)

Tasks are defined in scripts/eval_tasks/. Each task is a YAML file with:
  Required:
    - description: what the agent should do
    - verification: command to verify the result
    - expected_exit_code: 0 for success
    - origin: birth | stranger | second-incident | live
  Optional:
    - expected_reason: string that must appear in stdout/stderr
    - done_condition: shell command that exits 0 if task completed
    - protected_paths: list of paths the agent must not touch
    - max_diff_lines: diff size cap
    - oracle_question: what the oracle actually decides (makes proxy explicit)
    - attempts_to_green: agent-reported count of verify runs before the task
        passed. This is the efficiency pillar's core metric — a structured
        repo should drive it toward 1. Self-reported by the agent/harness that
        ran the task; the runner cannot observe it after the fact. Omitted =
        not measured (reported as "?"), never assumed to be 1.

Failed-to-load tasks (bad YAML, missing fields) count as failures in
the denominator, not skips. The rate is over all discovered files.

Usage:
    python scripts/run_evals.py                  # run all tasks
    python scripts/run_evals.py --task add-field # run one task
    python scripts/run_evals.py --baseline       # update baseline

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

VALID_ORIGINS = {"birth", "stranger", "second-incident", "live"}
REQUIRED_FIELDS = {"description", "verification", "expected_exit_code", "origin"}

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

    changed = []
    for line in lines[:-1]:
        parts = line.strip().split("|")
        if len(parts) >= 1:
            fname = parts[0].strip()
            if fname:
                changed.append(fname)

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
        if line.startswith("+") and not line.startswith("+++"):
            if SKIP_RE.search(line):
                count += 1
    return count


def uses_canonical_entry_point(verification: str) -> bool:
    """True if the verification command is the repo's documented interface.

    The efficiency pillar rests on "one command, no guessing". A task whose
    verification is `make verify` (or any `make <target>`) uses the entry point
    the Makefile and AGENTS.md advertise, so an agent never has to discover how
    to run it. A raw `pytest ...`, `python foo.py`, or bespoke shell pipeline is
    something the agent had to reconstruct — the token cost the cost table names.

    This is a proxy, not a token meter: it measures whether the check is reached
    through the documented door, not how many tokens the agent spent.
    """
    return verification.strip().startswith("make ")


def check_protected_paths(changed_files: list[str]) -> list[str]:
    """Return changed files that match CODEOWNERS-protected paths."""
    protected_prefixes = parse_codeowners()
    if not protected_prefixes:
        return []

    touched = []
    for f in changed_files:
        for prefix in protected_prefixes:
            clean = prefix.rstrip("*").rstrip("/")
            if f.startswith(clean):
                touched.append(f)
                break
    return touched


def validate_task(task: dict, task_path: Path) -> list[str]:
    """Return list of validation errors. Empty list means valid."""
    errors = []
    missing = REQUIRED_FIELDS - set(task.keys())
    if missing:
        errors.append(f"missing required fields: {', '.join(sorted(missing))}")

    origin = task.get("origin")
    if origin and origin not in VALID_ORIGINS:
        errors.append(
            f"origin '{origin}' not in {sorted(VALID_ORIGINS)}"
        )

    if "oracle_question" not in task:
        print(f"  ⚠ {task_path.name}: missing oracle_question — what does this oracle actually decide?")

    return errors


def run_task(task_path: Path) -> dict[str, object]:
    """Run a single eval task. Returns result dict.

    If the YAML fails to parse or is missing required fields, the task
    counts as a failure (not a skip). This keeps the denominator honest.
    """
    import yaml  # optional dep — only needed when running evals

    # Attempt to load and validate the task file
    try:
        task = yaml.safe_load(task_path.read_text())
    except Exception as e:
        return {
            "task": task_path.stem,
            "passed": False,
            "load_error": f"YAML parse error: {e}",
            "verify_pass": False,
            "reason_match": False,
            "done_condition_ok": False,
            "tests_disabled": 0,
            "protected_touched": [],
            "diff_lines": 0,
            "changed_files": [],
            "elapsed": 0,
            "origin": "unknown",
            "stdout": "",
            "stderr": "",
        }

    if not isinstance(task, dict):
        return {
            "task": task_path.stem,
            "passed": False,
            "load_error": "YAML did not produce a dict",
            "verify_pass": False,
            "reason_match": False,
            "done_condition_ok": False,
            "tests_disabled": 0,
            "protected_touched": [],
            "diff_lines": 0,
            "changed_files": [],
            "elapsed": 0,
            "origin": "unknown",
            "stdout": "",
            "stderr": "",
        }

    validation_errors = validate_task(task, task_path)
    if validation_errors:
        return {
            "task": task_path.stem,
            "passed": False,
            "load_error": "; ".join(validation_errors),
            "verify_pass": False,
            "reason_match": False,
            "done_condition_ok": False,
            "tests_disabled": 0,
            "protected_touched": [],
            "diff_lines": 0,
            "changed_files": [],
            "elapsed": 0,
            "origin": task.get("origin", "unknown"),
            "stdout": "",
            "stderr": "",
        }

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

    # Check expected_reason in output (stdout + stderr)
    # Proves the gate knows WHY it stopped, not just that it stopped.
    reason_match = True
    expected_reason = task.get("expected_reason")
    if expected_reason:
        combined_output = result.stdout + result.stderr
        reason_match = expected_reason in combined_output

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

    passed = (
        verify_pass
        and reason_match
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
        "reason_match": reason_match,
        "done_condition_ok": done_ok,
        "tests_disabled": tests_disabled,
        "protected_touched": [str(p) for p in protected_touched],
        "diff_lines": diff_lines,
        "changed_files": changed_files,
        "elapsed": round(elapsed, 2),
        "origin": task.get("origin", "unknown"),
        "attempts_to_green": task.get("attempts_to_green"),
        "canonical_entry_point": uses_canonical_entry_point(task["verification"]),
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

    # Denominator is ALL discovered files, including failed-to-load.
    # A task that can't load is a failure, not a skip.
    passed = sum(1 for r in results if r["passed"])
    failed_load = sum(1 for r in results if r.get("load_error"))
    total = len(results)
    rate = passed / total if total else 0.0

    print(f"\nEval results: {passed}/{total} passed ({rate:.0%})")
    if failed_load:
        print(f"  ⚠ {failed_load} task(s) failed to load (counted as failures)\n")
    else:
        print()

    for r in results:
        icon = "✓" if r["passed"] else "✗"

        if r.get("load_error"):
            print(f"  {icon} {r['task']} [LOAD ERROR: {r['load_error']}]")
            continue

        flags = []
        if not r.get("reason_match", True):
            flags.append("reason:missing")
        if r["tests_disabled"]:
            flags.append(f"skip:{r['tests_disabled']}")
        if r["protected_touched"]:
            flags.append(f"protected:{len(r['protected_touched'])}")
        if r["diff_lines"] > 0:
            flags.append(f"diff:{r['diff_lines']}")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        origin_str = f" ({r.get('origin', '?')})" if r.get("origin") else ""
        atg = r.get("attempts_to_green")
        atg_str = f" attempts:{atg}" if atg is not None else " attempts:?"
        door = "door:make" if r.get("canonical_entry_point") else "door:adhoc"
        print(
            f"  {icon} {r['task']} ({r['elapsed']}s){flag_str}{origin_str}"
            f" [{door}{atg_str}]"
        )

    # ── Efficiency pillar summary ────────────────────────────────────────
    # The safety pillar is proven by drills. The efficiency pillar is measured
    # here: how reachable the check is, and how many tries the agent needed.
    loaded = [r for r in results if not r.get("load_error")]
    if loaded:
        canonical = sum(1 for r in loaded if r.get("canonical_entry_point"))
        measured_atg = [
            r["attempts_to_green"]
            for r in loaded
            if r.get("attempts_to_green") is not None
        ]
        print("\nEfficiency:")
        print(
            f"  entry point: {canonical}/{len(loaded)} tasks verified via "
            f"`make` (the documented door, no discovery cost)"
        )
        if measured_atg:
            avg = sum(measured_atg) / len(measured_atg)
            print(
                f"  attempts to green: {len(measured_atg)}/{len(loaded)} "
                f"reported, mean {avg:.1f} (target 1.0)"
            )
        else:
            print(
                "  attempts to green: 0 tasks reported — add "
                "`attempts_to_green` to tasks to measure the cost claim"
            )

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
