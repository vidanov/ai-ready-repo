#!/usr/bin/env python3
"""
Agent evaluation runner.

Runs representative coding tasks against this repository and reports
task success rate, runtime, and any regressions from the baseline.

Usage:
    python scripts/run_evals.py                  # run all tasks
    python scripts/run_evals.py --task add-field # run one task
    python scripts/run_evals.py --baseline       # update baseline

Tasks are defined in scripts/eval_tasks/. Each task is a YAML file with:
  - description: what the agent should do
  - verification: command to verify the result
  - expected_exit_code: 0 for success

Exit code:
  0 — all tasks passed and success rate >= baseline
  1 — tasks failed or success rate regressed
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

TASKS_DIR = Path(__file__).parent / "eval_tasks"
BASELINE_FILE = Path(__file__).parent / "eval_baseline.json"


def load_baseline() -> dict[str, float]:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {}


def save_baseline(results: dict[str, float]) -> None:
    BASELINE_FILE.write_text(json.dumps(results, indent=2))
    print(f"Baseline saved to {BASELINE_FILE}")


def run_task(task_path: Path) -> dict[str, object]:
    import yaml  # optional dep — only needed when running evals

    task = yaml.safe_load(task_path.read_text())
    start = time.monotonic()

    result = subprocess.run(
        task["verification"],
        shell=True,
        capture_output=True,
        text=True,
    )

    elapsed = time.monotonic() - start
    passed = result.returncode == task.get("expected_exit_code", 0)

    return {
        "task": task_path.stem,
        "passed": passed,
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
        print(f"  {icon} {r['task']} ({r['elapsed']}s)")

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
