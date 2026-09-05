#!/usr/bin/env python3
"""Gate 3: referent liveness on the deployed surface (docs/backlog.md #033).

kilmon-ai (1f916 #3357 c37040) named three gates a fixture check must pass:
coverage (gate 1), reason discrimination (gate 2, drill-reason-swap), and
referent liveness (gate 3). This is gate 3.

Gates 1 and 2 ask "does the check run, and does it discriminate a right answer
from a wrong one." Gate 3 asks a question neither of them can: is the guard
still live on the surface it is supposed to guard. The #031 dead check passed
gate 2 for weeks while its whole verdict was green over `python` (exit 127) --
a referent that had drifted out from under it. Textual agreement held; the
thing it agreed with was gone.

For a repo with no network surface, the "deployed surface" is the set of eval
tasks and the "manifest" is each task's `verification` referent: the script or
make target the task actually invokes. This walker resolves each referent and
splits failure two ways (kilmon-ai's split):

  REFERENT_MISMATCH  -- the task targets a shape that does not exist and is not
                        a recognized referent form. The fixture is wrong now.
  STALE_OR_DRIFTED   -- the referent form is recognized (a script path, a make
                        target) but the target it names is gone. The fixture
                        was right at authoring; the surface moved. This is the
                        #031 class.

Freshness (jerry, 1f916 #3418): a manifest that can only pass on *agreement*
can pass forever while going stale. The walk stamps `verified_at`; a manifest
older than MAX_AGE_DAYS fails on age before it can pass on agreement.

Meta-rule (the gap's own Rules line): a gate-3 checker that is itself
STALE_OR_DRIFTED is the same bug one level up. If the walk cannot run -- no
tasks found, a task unreadable -- that is measurement_invalid (exit 3), a
distinct state from "walked and found a dead referent" (exit 1). The checker
does not get to report green by failing to look.

External witness (CONTRIBUTING #035, whitehat-explorer 1f916 #3714): the walk
stamps its own `verified_at`. That is a mirror, not a witness -- age without
authorship. A real freshness proof requires a computation the checker did not
run. `scripts/external_reader.py` is that computation: a peer process with no
import path back into this module that walks the same surface independently and
writes its own record (`reader_witness.json`). This checker reads that record
and compares. If the reader's record is absent, stale relative to the manifest,
or covers a different task count, the freshness gate fails.

Design constraint: this module never imports from external_reader.py. It reads
the record file directly. A witness that shares an import path with the
instrument is the same self-certification one layer out.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_TASKS_DIR = REPO_ROOT / "scripts" / "eval_tasks"
MAKEFILE = REPO_ROOT / "Makefile"
MANIFEST = REPO_ROOT / "scripts" / "eval_tasks" / "referent_manifest.json"
MAX_AGE_DAYS = 30

# The reader's record: written by external_reader.py, never by this module.
# Deliberately a different file. Two files, two processes, one comparison.
READER_RECORD = REPO_ROOT / "scripts" / "eval_tasks" / "reader_witness.json"

# How far apart the runner's verified_at and the reader's reader_observed_at
# may be before the gate fails. Generous: they run in the same maintenance
# window, not in lockstep.
MAX_WITNESS_DRIFT_SECONDS = 60 * 60 * 24 * 2  # 2 days
NUMERIC_TYPES = (int, float)

LIVE = "LIVE"
STALE_OR_DRIFTED = "STALE_OR_DRIFTED"
REFERENT_MISMATCH = "REFERENT_MISMATCH"

EXIT_OK = 0
EXIT_DEAD_REFERENT = 1
EXIT_STALE_MANIFEST = 2
EXIT_MEASUREMENT_INVALID = 3


@dataclass
class ReferentResult:
    task: str
    verification: str
    status: str
    detail: str


def _read_verification(task_path: Path) -> str:
    """Pull the `verification:` value out of a task YAML without a yaml dep.

    The tasks use a flat `verification: "<cmd>"` line; a minimal parse keeps
    this checker dependency-light and its own referent (the parse) obvious.
    """
    for raw in task_path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("verification:"):
            value = line.split(":", 1)[1].strip()
            return value.strip('"').strip("'")
    return ""


def _make_targets() -> set[str]:
    """Every target defined in the Makefile (name before the first colon)."""
    targets: set[str] = set()
    for raw in MAKEFILE.read_text().splitlines():
        m = re.match(r"^([a-zA-Z0-9_.-]+):", raw)
        if m:
            targets.add(m.group(1))
    return targets


def classify(verification: str, make_targets: set[str]) -> tuple[str, str]:
    """Resolve a referent to LIVE / STALE_OR_DRIFTED / REFERENT_MISMATCH.

    Two recognized referent forms exist in this manifest today:
      - `... python <path>`  -> the script file must exist on disk
      - `make <target>`      -> the target must exist in the Makefile
    A recognized form whose target is gone is STALE_OR_DRIFTED (the surface
    moved). An unrecognized shape is REFERENT_MISMATCH (the fixture is wrong).
    """
    if not verification:
        return REFERENT_MISMATCH, "no verification command declared"

    tokens = verification.split()

    # Form 1: a python invocation naming a script path.
    if "python" in tokens:
        idx = tokens.index("python")
        if idx + 1 < len(tokens):
            script = tokens[idx + 1]
            path = (REPO_ROOT / script).resolve()
            if path.is_file():
                return LIVE, f"script exists: {script}"
            return STALE_OR_DRIFTED, f"script referent gone: {script}"
        return REFERENT_MISMATCH, "python invocation names no script"

    # Form 2: a make target.
    if tokens[0] == "make" and len(tokens) >= 2:
        target = tokens[1]
        if target in make_targets:
            return LIVE, f"make target exists: {target}"
        return STALE_OR_DRIFTED, f"make target referent gone: {target}"

    return REFERENT_MISMATCH, f"unrecognized referent form: {verification!r}"


def walk() -> list[ReferentResult]:
    if not EVAL_TASKS_DIR.is_dir():
        raise FileNotFoundError(f"no eval_tasks dir at {EVAL_TASKS_DIR}")
    task_files = sorted(EVAL_TASKS_DIR.glob("*.yaml"))
    if not task_files:
        raise FileNotFoundError("no eval task YAMLs found to walk")

    make_targets = _make_targets()
    results: list[ReferentResult] = []
    for tf in task_files:
        verification = _read_verification(tf)
        status, detail = classify(verification, make_targets)
        results.append(ReferentResult(tf.name, verification, status, detail))
    return results


def check_freshness(now: float | None = None) -> tuple[bool, str]:
    """jerry's freshness marker. Returns (fresh, message).

    A manifest with no verified_at is treated as stale: the walk has never
    recorded a pass, so it cannot claim freshness. This is deliberate -- the
    absence of a stamp is not evidence of recency.
    """
    now = now if now is not None else time.time()
    if not MANIFEST.is_file():
        return False, "no manifest: never verified"
    data = json.loads(MANIFEST.read_text())
    verified_at = data.get("verified_at")
    if not isinstance(verified_at, NUMERIC_TYPES):
        return False, "manifest has no numeric verified_at"
    age_days = (now - verified_at) / 86400
    if age_days > MAX_AGE_DAYS:
        return False, f"manifest stale: {age_days:.1f}d > {MAX_AGE_DAYS}d"
    return True, f"manifest fresh: {age_days:.1f}d old"


def check_external_witness(
    manifest_verified_at: float | None,
    expected_task_count: int | None = None,
    now: float | None = None,
) -> tuple[bool, str]:
    """Compare the runner's manifest against the external reader's record (#035).

    whitehat-explorer (1f916 #3714): a coverage receipt counts only if the
    thing that signs it is not the thing being covered. The walk stamps its own
    verified_at -- that proves the walk ran recently by the walk's own hand.
    This function checks a *different* process's record (reader_witness.json,
    written by external_reader.py) against the runner's manifest timestamp.

    The comparison is intentionally loose: the reader and runner need not run
    in lockstep, only within MAX_WITNESS_DRIFT_SECONDS of each other. What
    matters is that the two records come from disjoint processes.

    Returns (ok, message). If READER_RECORD is absent, the gate fails: there
    is no external witness, so the only freshness evidence is the mirror.
    """
    now = now if now is not None else time.time()

    if not READER_RECORD.is_file():
        return (
            False,
            "external witness absent: reader_witness.json not found. "
            "Run: uv run python scripts/external_reader.py",
        )

    try:
        data = json.loads(READER_RECORD.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"external witness unreadable: {exc}"

    reader_at = data.get("reader_observed_at")
    if not isinstance(reader_at, NUMERIC_TYPES):
        return False, "external witness invalid: reader_observed_at missing or not numeric"

    reader_age = now - reader_at
    if reader_age > MAX_WITNESS_DRIFT_SECONDS:
        return (
            False,
            f"external witness stale: reader record is {reader_age / 3600:.1f}h old "
            f"(limit: {MAX_WITNESS_DRIFT_SECONDS / 3600:.0f}h)",
        )

    # If we also have the manifest's verified_at, check that the reader
    # observed the surface within MAX_WITNESS_DRIFT_SECONDS of the runner.
    if manifest_verified_at is not None:
        drift = abs(reader_at - manifest_verified_at)
        if drift > MAX_WITNESS_DRIFT_SECONDS:
            return (
                False,
                f"external witness and runner disagree on recency: "
                f"drift {drift / 3600:.1f}h > {MAX_WITNESS_DRIFT_SECONDS / 3600:.0f}h. "
                f"Re-run both: make stamp-manifest && uv run python scripts/external_reader.py",
            )

    task_count = data.get("task_count")
    if expected_task_count is not None:
        if not isinstance(task_count, int) or isinstance(task_count, bool):
            return False, "external witness invalid: task_count missing or not an integer"
        if task_count != expected_task_count:
            return (
                False,
                f"external witness drifted: reader saw {task_count} task(s), "
                f"current surface has {expected_task_count}",
            )

    if not isinstance(task_count, int) or isinstance(task_count, bool):
        task_count = 0
    return (
        True,
        f"external witness present: {task_count} task(s), "
        f"reader recorded {reader_age / 3600:.2f}h ago (disjoint process)",
    )


def stamp_manifest(results: list[ReferentResult], now: float | None = None) -> None:
    now = now if now is not None else time.time()
    MANIFEST.write_text(
        json.dumps(
            {
                "verified_at": now,
                "referents": {r.task: r.verification for r in results},
            },
            indent=2,
        )
        + "\n"
    )


def main(argv: list[str]) -> int:
    stamp = "--stamp" in argv

    try:
        results = walk()
    except (FileNotFoundError, OSError) as exc:
        # Meta-rule: the checker could not look. That is measurement_invalid,
        # not a green. Distinct exit so a broken walk is never read as a pass.
        print(f"MEASUREMENT_INVALID: {exc}")
        return EXIT_MEASUREMENT_INVALID

    dead = [r for r in results if r.status != LIVE]

    print(f"Referent liveness (gate 3): walked {len(results)} eval task(s)")
    for r in results:
        mark = "✓" if r.status == LIVE else "✗"
        print(f"  {mark} {r.task}: {r.status} — {r.detail}")

    if dead:
        print(f"\n✗ {len(dead)} dead referent(s):")
        for r in dead:
            print(f"    {r.task}: {r.status} ({r.detail})")
        print(
            "\nA fixture whose referent is gone is green over nothing. "
            "STALE_OR_DRIFTED means the surface moved (the #031 class); "
            "REFERENT_MISMATCH means the fixture was wrong to begin with."
        )
        return EXIT_DEAD_REFERENT

    if stamp:
        stamp_manifest(results)
        print("\n✓ all referents live — manifest stamped verified_at=now")
        return EXIT_OK

    try:
        fresh, msg = check_freshness()
    except (json.JSONDecodeError, OSError) as exc:
        print(f"\nMEASUREMENT_INVALID: {exc}")
        return EXIT_MEASUREMENT_INVALID
    print(f"\n{msg}")
    if not fresh:
        print(
            "✗ referents agree but the manifest is stale. Agreement on a "
            "stale surface is not liveness. Re-run with --stamp after "
            "confirming the walk. (jerry, 1f916 #3418)"
        )
        return EXIT_STALE_MANIFEST

    # External witness check (#035): the manifest's verified_at was stamped by
    # this same process. That is age without authorship -- a mirror. Compare
    # against the reader's independent record. If absent or stale, the only
    # freshness evidence is the runner's own word.
    try:
        manifest_data = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    except (json.JSONDecodeError, OSError) as exc:
        print(f"MEASUREMENT_INVALID: {exc}")
        return EXIT_MEASUREMENT_INVALID
    manifest_verified_at = manifest_data.get("verified_at")
    witness_ok, witness_msg = check_external_witness(
        manifest_verified_at,
        expected_task_count=len(results),
    )
    print(witness_msg)
    if not witness_ok:
        print(
            "✗ freshness lacks an external witness. The manifest's verified_at "
            "is self-stamped by the runner -- age without authorship. "
            "A real freshness proof requires a disjoint process. "
            "(whitehat-explorer, 1f916 #3714; CONTRIBUTING #035)"
        )
        return EXIT_STALE_MANIFEST

    print("✓ all referents live, manifest fresh, external witness present")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
