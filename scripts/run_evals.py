#!/usr/bin/env python3
"""
Verification regression runner.

Runs verification commands against this repository and reports task success,
runtime, and measurement coverage. It does not execute agent coding tasks.

Records these dimensions per task:
  - verify_pass: did the verification command exit as expected?
  - reason_match: did the output contain the expected_reason string?
  - done_condition: did the task's specific done-condition pass?
  - tests_disabled: did the agent skip/xfail tests to make them pass?
  - protected_touched: did the agent modify CODEOWNERS-protected paths?
  - diff_lines: total insertions + deletions (scope creep signal)
  - origin: where the task came from (birth/stranger/second-incident/live)
  - verdict: ran_passed / ran_failed / measurement_invalid. The last is
      disjoint from the first two — a task whose door did not run (exit 126/127)
      carries no evidence and is excluded from the pass/fail rate rather than
      counted as a failure. Proposed on 1f916 #3539 (jerry, terry-synctzn);
      the negative drill is `make drill-measurement-invalid`.

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

Failed-to-load tasks lower measurement coverage and are excluded from the
pass/fail rate. Every measurable task must pass, regardless of the baseline.
Baseline updates require the same passing checks and coverage floor.

Usage:
    python scripts/run_evals.py                  # run all tasks
    python scripts/run_evals.py --task add-field # run one task
    python scripts/run_evals.py --baseline       # update baseline

Exit code:
  0 — all measurable tasks passed and measurement coverage met its floor
  1 — tasks failed, no tasks matched, or measurement coverage was below its floor
"""

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
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
    r"\bxit\(",  # Jasmine/Jest
    r"\bxdescribe\(",  # Jasmine/Jest
    r"\.skip\(",  # Mocha/Vitest
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


# Verdict output space (proposed on 1f916 #3539 by jerry c36960 and
# terry-synctzn c37020, refined c37026/c37070/c37100). MEASUREMENT_INVALID
# must be DISJOINT from the subject's ordinary verdicts: an aggregate must
# never count "could not run" as a pass or a fail. A 127 and a genuine
# failure both read as "not passing" only when the output space collapses
# them into one bit — which is exactly how a dead check stayed invisible for
# four days (docs/backlog.md #031).
VERDICT_RAN_PASSED = "ran_passed"
VERDICT_RAN_FAILED = "ran_failed"
VERDICT_MEASUREMENT_INVALID = "measurement_invalid"

# Shell exit codes that mean the command never executed the subject, so the
# result carries no evidence about pass/fail: 127 = command not found,
# 126 = found but not executable.
UNREACHABLE_EXIT_CODES = {126, 127}

# Minimum share of runs that must be valid measurements for the pass rate to be
# called healthy (jerry c37451 + latex c37440, 1f916 #3539). Disjointness alone
# lets the rate read 100% as the harness rots — 9 corpses + 1 pass reports 1/1.
# Coverage is the unomittable companion; below this floor the rate is not
# trustworthy no matter how green, and the run exits nonzero.
MEASUREMENT_COVERAGE_FLOOR = 0.75


def classify_run(exit_code: int, expected_exit_code: int) -> tuple[bool, bool, str]:
    """Map a subprocess result to (reachable, executed, verdict).

    - unreachable (126/127): the door does not resolve to a runnable command,
      so we have no evidence about the subject -> measurement_invalid.
    - reachable and matches expected exit -> ran_passed.
    - reachable but wrong exit -> ran_failed.

    measurement_invalid is disjoint from ran_passed/ran_failed by construction:
    the aggregate treats it as neither, so a corpse cannot be absorbed into a
    green rate nor hidden inside a red one.
    """
    if exit_code in UNREACHABLE_EXIT_CODES:
        return (False, False, VERDICT_MEASUREMENT_INVALID)
    if exit_code == expected_exit_code:
        return (True, True, VERDICT_RAN_PASSED)
    return (True, True, VERDICT_RAN_FAILED)


@dataclass
class EvalReceipt:
    """The single definition of a per-task result shape.

    Every path through run_task() produces one of these, so a downstream reader
    never meets a missing key. Before this existed the shape was hand-built in
    four places and the three error paths had drifted — they omitted verdict,
    reachable, executed, so a load-error row silently escaped the
    measurement_invalid output-space invariant (1f916 #3539). One definition
    closes that gap by construction.
    """

    task: str
    origin: str = "unknown"
    load_error: str | None = None
    verify_pass: bool = False
    reason_match: bool = False
    done_condition_ok: bool = False
    tests_disabled: int = 0
    protected_touched: list[str] = field(default_factory=list)
    diff_lines: int = 0
    changed_files: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    attempts_to_green: int | None = None
    canonical_entry_point: bool = False
    reachable: bool = False
    executed: bool = False
    verdict: str = VERDICT_MEASUREMENT_INVALID
    door: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    # Two-stage coverage gate (axiom-sovereign, 1f916 #3595). exercised_axes is
    # recorded from real evidence of what the run did; missing_required_axes is
    # the task's required set minus what was exercised. A non-empty
    # missing_required_axes forces measurement_invalid — an unexercised required
    # dimension is a measurement gap, not a subject pass or fail.
    exercised_axes: list[str] = field(default_factory=list)
    missing_required_axes: list[str] = field(default_factory=list)

    @classmethod
    def load_error_receipt(cls, task: str, reason: str, origin: str = "unknown") -> "EvalReceipt":
        """A file that cannot load carries no evidence about the subject.

        It is measurement_invalid, not a failure — the same disjoint bucket as a
        127. This is more correct than the old behavior (passed=False, no
        verdict), which let the aggregate read a broken file as an ordinary fail.
        """
        return cls(task=task, origin=origin, load_error=reason)

    @property
    def passed(self) -> bool:
        """The scoring rule, in one named place.

        measurement_invalid and load errors are never 'passed'. A real pass
        requires the run to have executed and cleared every gate.
        """
        if self.load_error is not None:
            return False
        if self.missing_required_axes:
            return False
        if self.verdict != VERDICT_RAN_PASSED:
            return False
        return (
            self.verify_pass
            and self.reason_match
            and self.done_condition_ok
            and self.tests_disabled == 0
            and not self.protected_touched
            and not self.changed_files_touch_protected
        )

    # Set by run_task after protected-path checks; kept separate from
    # protected_touched (CODEOWNERS) because task-level protected_paths are a
    # different source. Both must be clear to pass.
    changed_files_touch_protected: bool = False

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        # 'passed' is a property, not a field; asdict drops it. The aggregate
        # and report read r["passed"], so materialize it.
        d["passed"] = self.passed
        # Internal scoring helper, not part of the public receipt.
        d.pop("changed_files_touch_protected", None)
        return d


def uses_canonical_entry_point(verification: str) -> bool:
    """Record Make usage; this does not measure discovery effort or token cost."""
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
        errors.append(f"origin '{origin}' not in {sorted(VALID_ORIGINS)}")

    if "oracle_question" not in task:
        print(
            f"  ⚠ {task_path.name}: missing oracle_question — "
            "what does this oracle actually decide?"
        )

    return errors


def run_task(task_path: Path) -> dict[str, object]:
    """Run a single eval task. Returns result dict.

    If the YAML fails to parse or is missing required fields, the task
    counts as a failure (not a skip). This keeps the denominator honest.
    """
    import yaml  # optional dep — only needed when running evals

    name = task_path.stem

    # Attempt to load and validate the task file. Every failure path returns a
    # complete receipt via load_error_receipt (verdict=measurement_invalid),
    # so a broken file cannot slip through with a partial dict.
    try:
        task = yaml.safe_load(task_path.read_text())
    except Exception as e:
        return EvalReceipt.load_error_receipt(name, f"YAML parse error: {e}").to_dict()

    if not isinstance(task, dict):
        return EvalReceipt.load_error_receipt(name, "YAML did not produce a dict").to_dict()

    validation_errors = validate_task(task, task_path)
    if validation_errors:
        return EvalReceipt.load_error_receipt(
            name, "; ".join(validation_errors), origin=task.get("origin", "unknown")
        ).to_dict()

    start = time.monotonic()
    result = subprocess.run(task["verification"], shell=True, capture_output=True, text=True)
    elapsed = time.monotonic() - start
    expected_exit = task.get("expected_exit_code", 0)
    reachable, executed, verdict = classify_run(result.returncode, expected_exit)

    # Does the gate know WHY it stopped, not just that it stopped?
    reason_match = True
    expected_reason = task.get("expected_reason")
    if expected_reason:
        reason_match = expected_reason in (result.stdout + result.stderr)

    done_ok = True
    if "done_condition" in task:
        done_result = subprocess.run(
            task["done_condition"], shell=True, capture_output=True, text=True
        )
        done_ok = done_result.returncode == 0

    diff_lines, changed_files = get_diff_stats()
    tests_disabled = count_tests_disabled_in_diff()
    protected_touched = check_protected_paths(changed_files)

    # A max_diff_lines cap breach or a task-declared protected-path touch both
    # disqualify the run. Fold them into changed_files_touch_protected so the
    # receipt's passed property sees a single "extra constraint failed" signal.
    max_diff = task.get("max_diff_lines")
    diff_over_cap = max_diff is not None and diff_lines > max_diff

    extra_protected = False
    for pat in task.get("protected_paths", []):
        clean = pat.lstrip("/")
        if any(f.startswith(clean) for f in changed_files):
            extra_protected = True
            break

    # Axes actually exercised, recorded from real evidence (axiom-sovereign
    # #3595). reachability whenever the subject ran; reason only when the task
    # declared expected_reason AND it was checked; done_condition only when the
    # task declared one. Required axes come from the TASK, not the receipt, so a
    # receipt cannot pass by omitting an axis. An unexercised required axis is a
    # measurement gap, not a pass or fail: it forces measurement_invalid.
    exercised = []
    if executed:
        exercised.append("reachability")
    if task.get("expected_reason"):
        exercised.append("reason")
    if "done_condition" in task:
        exercised.append("done_condition")
    required = task.get("required_axes", [])
    missing = [ax for ax in required if ax not in exercised]
    if missing:
        verdict = VERDICT_MEASUREMENT_INVALID

    receipt = EvalReceipt(
        task=name,
        origin=task.get("origin", "unknown"),
        verify_pass=result.returncode == expected_exit,
        reason_match=reason_match,
        done_condition_ok=done_ok,
        tests_disabled=tests_disabled,
        protected_touched=[str(p) for p in protected_touched],
        diff_lines=diff_lines,
        changed_files=changed_files,
        elapsed=round(elapsed, 2),
        attempts_to_green=task.get("attempts_to_green"),
        canonical_entry_point=uses_canonical_entry_point(task["verification"]),
        reachable=reachable,
        executed=executed,
        verdict=verdict,
        door=task["verification"],
        exit_code=result.returncode,
        stdout=result.stdout[:500],
        stderr=result.stderr[:500],
        changed_files_touch_protected=diff_over_cap or extra_protected,
        exercised_axes=exercised,
        missing_required_axes=missing,
    )
    return receipt.to_dict()


@dataclass
class EvalAggregate:
    """Two axes, kept separate on purpose (1f916 #3539).

    - pass rate (passed/total): over MEASURABLE tasks only. A corpse is never
      counted as a pass or a fail — that disjointness is the PR #42 invariant.
    - coverage (valid_runs/total_runs): over ALL runs. This is the axis latex
      named as missing: dropping invalid rows from the pass denominator lets the
      rate read 100% while the harness rots. Coverage cannot be omitted, and
      coverage_ok gates whether the rate is trustworthy at all.
    """

    passed: int
    total: int
    rate: float
    valid_runs: int
    total_runs: int
    coverage: float
    coverage_ok: bool
    failed_load: int


def aggregate(results: list[dict], floor: float = MEASUREMENT_COVERAGE_FLOOR) -> EvalAggregate:
    """Compute both axes from per-task receipts.

    A measurement is invalid whenever verdict == measurement_invalid — which
    includes load errors (a file that can't load carries no evidence). Those
    invalid runs are pulled from the pass/fail denominator but stay in the
    coverage denominator, so a run that is all corpses cannot launder itself
    into a healthy-looking rate.
    """
    total_runs = len(results)
    invalid = [r for r in results if r.get("verdict") == VERDICT_MEASUREMENT_INVALID]
    measurable = [r for r in results if r.get("verdict") != VERDICT_MEASUREMENT_INVALID]

    passed = sum(1 for r in measurable if r.get("passed"))
    total = len(measurable)
    rate = passed / total if total else 0.0

    valid_runs = total_runs - len(invalid)
    coverage = valid_runs / total_runs if total_runs else 0.0
    # An empty run has no coverage to defend; a run with any tasks must clear
    # the floor.
    coverage_ok = total_runs == 0 or coverage >= floor

    failed_load = sum(1 for r in results if r.get("load_error"))
    return EvalAggregate(
        passed=passed,
        total=total,
        rate=rate,
        valid_runs=valid_runs,
        total_runs=total_runs,
        coverage=coverage,
        coverage_ok=coverage_ok,
        failed_load=failed_load,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run verification regression tasks")
    parser.add_argument("--task", help="Run a single task by name")
    parser.add_argument("--baseline", action="store_true", help="Update baseline")
    args = parser.parse_args()

    if not TASKS_DIR.exists():
        print(f"No eval tasks found at {TASKS_DIR}/")
        print("Add YAML task files to get started.")
        return 1

    task_files = sorted(TASKS_DIR.glob("*.yaml"))
    if args.task:
        task_files = [t for t in task_files if t.stem == args.task]

    if not task_files:
        print("No matching tasks found.")
        return 1

    results = [run_task(t) for t in task_files]

    # Two axes, computed once (1f916 #3539). See aggregate() for why pass rate
    # and coverage use different denominators.
    agg = aggregate(results)
    invalid = [
        r
        for r in results
        if not r.get("load_error") and r.get("verdict") == VERDICT_MEASUREMENT_INVALID
    ]
    passed, total, rate = agg.passed, agg.total, agg.rate

    print(f"\nEval results: {passed}/{total} passed ({rate:.0%})")
    # Coverage is reported next to the rate, always, so a green number can never
    # be read without knowing how much of the harness was even measurable.
    print(
        f"Measurement coverage: {agg.valid_runs}/{agg.total_runs} runs valid "
        f"({agg.coverage:.0%}, floor {MEASUREMENT_COVERAGE_FLOOR:.0%})"
    )
    if invalid:
        print(
            f"  ⚠ {len(invalid)} task(s) MEASUREMENT_INVALID — door did not run, "
            f"NOT counted as pass or fail:"
        )
        for r in invalid:
            miss = r.get("missing_required_axes") or []
            if miss:
                print(
                    f"      {r['task']}: missing required axes {miss} — "
                    f"a required dimension was never exercised (not scored)"
                )
            else:
                print(
                    f"      {r['task']}: exit {r.get('exit_code')} on "
                    f"`{r.get('door')}` (reachable={r.get('reachable')})"
                )
    if agg.failed_load:
        print(
            f"  ⚠ {agg.failed_load} task(s) failed to load "
            f"(measurement_invalid — they lower coverage)\n"
        )
    else:
        print()

    for r in results:
        if r.get("verdict") == VERDICT_MEASUREMENT_INVALID:
            icon = "⊘"  # neither pass nor fail — measurement invalid
        else:
            icon = "✓" if r["passed"] else "✗"

        if r.get("load_error"):
            print(f"  ✗ {r['task']} [LOAD ERROR: {r['load_error']}]")
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
        print(f"  {icon} {r['task']} ({r['elapsed']}s){flag_str}{origin_str} [{door}{atg_str}]")

    # ── Efficiency pillar summary ────────────────────────────────────────
    # Task metadata is descriptive; it does not establish agent efficiency.
    loaded = [r for r in results if not r.get("load_error")]
    if loaded:
        canonical = sum(1 for r in loaded if r.get("canonical_entry_point"))
        measured_atg = [
            r["attempts_to_green"] for r in loaded if r.get("attempts_to_green") is not None
        ]
        print("\nEntry-point metadata (not an agent performance benchmark):")
        print(
            f"  entry point: {canonical}/{len(loaded)} tasks verified via "
            "`make` (command convention only)"
        )
        if measured_atg:
            avg = sum(measured_atg) / len(measured_atg)
            print(
                f"  attempts to green: {len(measured_atg)}/{len(loaded)} "
                f"reported, mean {avg:.1f} (target 1.0)"
            )
        else:
            print(
                "  attempts to green: 0 tasks reported — "
                "recorded agent runs are required to evaluate the efficiency hypothesis"
            )

    baseline = load_baseline()
    prior_rate = baseline.get("success_rate", 0.0)

    if not agg.coverage_ok:
        print(
            f"\n✗ Measurement coverage {agg.coverage:.0%} below floor "
            f"{MEASUREMENT_COVERAGE_FLOOR:.0%}: the pass rate is not trustworthy. "
            f"{agg.total_runs - agg.valid_runs} of {agg.total_runs} runs never "
            f"reached the subject. A green rate over a rotting harness is the "
            f"original dead-check bug one level up (1f916 #3539)."
        )
        return 1

    if passed != total:
        print(f"\n✗ {total - passed} verification task(s) failed; baseline cannot waive failures.")
        return 1

    if args.baseline:
        save_baseline({"success_rate": rate, "tasks": total})
        return 0

    print(f"\n✓ Success rate {rate:.0%} (baseline {prior_rate:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
