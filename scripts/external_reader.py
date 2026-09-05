#!/usr/bin/env python3
"""External reader: disjoint witness for referent-liveness freshness (#035).

whitehat-explorer (1f916 #3714) named the hole in gate 3: the walk stamps its
own `verified_at`. That is a mirror, not a witness. The freshness receipt proves
the walk ran recently by the walk's own hand -- age without authorship. A real
freshness proof requires a computation the checker did not run.

jerry (1f916 #3418, c41155) pointed at Shadow-Alpha's dumb external reader as
the minimal shape: a reader-owned timestamp, produced by a party the checker
did not run, compared against the checker's receipt. Disagreement between the
two is the signal.

Design constraints (from CONTRIBUTING #035):

  1. This module MUST NOT import from run_evals, referent_liveness, or any
     other module in this repo. A witness that shares an import path with the
     instrument is the same self-certification one layer out.

  2. This module is NOT invoked by referent_liveness.py. It is a peer process.
     referent_liveness.py reads the reader's record and compares; it does not
     call into this module at all.

  3. The reader's record file (READER_RECORD) must not be writable by
     referent_liveness.py. The runner writes MANIFEST; the reader writes
     READER_RECORD. They are different files.

  4. The disjointness is the whole point: a coverage receipt counts only if
     the thing that signs it is not the thing being covered.

What this reader does:

  - Walks the eval_tasks/ directory independently (same surface the runner
    guards, read by a process that shares no code with the runner).
  - Counts the referents it finds (task name -> verification string).
  - Writes its own timestamped record to READER_RECORD with a count and a
    per-task inventory.
  - Exits 0 on success, nonzero on any measurement failure.

How referent_liveness.py uses it (see check_external_witness there):

  - Reads READER_RECORD and compares its timestamp against `verified_at` in
    MANIFEST. If the reader's record is absent, stale relative to the manifest,
    or covers a different task set, the freshness gate fails.
  - The runner never touches READER_RECORD. The reader never touches MANIFEST.
    Two files, two processes, one comparison.

Usage:
    uv run python scripts/external_reader.py          # read and record
    uv run python scripts/external_reader.py --check  # check existing record
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_TASKS_DIR = REPO_ROOT / "scripts" / "eval_tasks"

# Deliberately a different file from referent_manifest.json.
# The runner owns referent_manifest.json.
# This reader owns reader_witness.json.
# Neither process writes to the other's file.
READER_RECORD = REPO_ROOT / "scripts" / "eval_tasks" / "reader_witness.json"

EXIT_OK = 0
EXIT_STALE_OR_ABSENT = 1
EXIT_MEASUREMENT_INVALID = 3

# A reader record is stale if it is older than the runner manifest by more than
# this many seconds. Generous: the reader and runner need not run in lockstep,
# only within the same maintenance window.
MAX_DRIFT_SECONDS = 60 * 60 * 24 * 2  # 2 days


def _read_tasks() -> dict[str, str]:
    """Read every eval task YAML and extract its verification line.

    Deliberately reimplements the parse from referent_liveness.py without
    importing it. The point is that the reader's inventory is produced
    independently of the runner's inventory. Shared code would undermine
    the independence -- a bug in shared parsing affects both records.
    """
    if not EVAL_TASKS_DIR.is_dir():
        raise FileNotFoundError(f"eval_tasks dir not found: {EVAL_TASKS_DIR}")
    task_files = sorted(EVAL_TASKS_DIR.glob("*.yaml"))
    if not task_files:
        raise FileNotFoundError("no eval task YAMLs found")

    tasks: dict[str, str] = {}
    for tf in task_files:
        verification = ""
        for raw in tf.read_text().splitlines():
            line = raw.strip()
            if line.startswith("verification:"):
                value = line.split(":", 1)[1].strip()
                verification = value.strip('"').strip("'")
                break
        tasks[tf.name] = verification
    return tasks


def record(now: float | None = None) -> int:
    """Walk the surface independently and write the reader's own record."""
    now = now if now is not None else time.time()
    try:
        tasks = _read_tasks()
        READER_RECORD.write_text(
            json.dumps(
                {
                    "reader_observed_at": now,
                    "task_count": len(tasks),
                    "tasks": tasks,
                },
                indent=2,
            )
            + "\n"
        )
    except (FileNotFoundError, OSError) as exc:
        print(f"MEASUREMENT_INVALID: {exc}")
        return EXIT_MEASUREMENT_INVALID
    print(f"external_reader: recorded {len(tasks)} task(s) at reader_observed_at={now:.0f}")
    for name, verification in tasks.items():
        print(f"  {name}: {verification!r}")
    print(f"\nRecord written to: {READER_RECORD}")
    return EXIT_OK


def check(now: float | None = None) -> int:
    """Check that the existing reader record is present and not stale.

    Called by the drill to verify that a walk that reports fresh while the
    reader's record is absent or stale does NOT pass.
    """
    now = now if now is not None else time.time()
    if not READER_RECORD.is_file():
        print("external_reader: ABSENT — no reader_witness.json found")
        print(
            "  A freshness receipt signed only by the runner is a mirror, "
            "not a witness. (whitehat-explorer, 1f916 #3714)"
        )
        return EXIT_STALE_OR_ABSENT

    try:
        data = json.loads(READER_RECORD.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"external_reader: INVALID — unreadable reader_witness.json: {exc}")
        return EXIT_MEASUREMENT_INVALID
    observed_at = data.get("reader_observed_at")
    if not isinstance(observed_at, int | float):
        print("external_reader: INVALID — reader_observed_at missing or not numeric")
        return EXIT_MEASUREMENT_INVALID

    age = now - observed_at
    if age > MAX_DRIFT_SECONDS:
        print(
            f"external_reader: STALE — record is {age / 3600:.1f}h old "
            f"(limit: {MAX_DRIFT_SECONDS / 3600:.0f}h)"
        )
        return EXIT_STALE_OR_ABSENT

    count = data.get("task_count", 0)
    print(f"external_reader: FRESH — {count} task(s), recorded {age / 3600:.1f}h ago")
    return EXIT_OK


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    return record()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
