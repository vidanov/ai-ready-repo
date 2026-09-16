"""Re-coupling harness: measure the one term the N-version literature has no clean
precedent for — decay of reader decorrelation over time as planted sets leak into
the training corpus.

Context (1f916 #5417). The correlation two readers share splits into two terms
(paste "The shared-brain term is constructible", 2026-09-16, ai-ready-repo-v2):

  1. the shared-brain term — for agents, drivable toward zero by construction
     (different weights, withheld answer, a frozen non-learning verifier); and
  2. the shared-difficulty term — the Knight & Leveson (1986) floor: independently
     built readers still miss the input that is genuinely hard. Construction does
     not reach it. It is the term that earns measurement.

Design diversity in aerospace is static. Ours rots: every planted set we publish
becomes training corpus for the next reader generation, so a representation with
"no idiom" for a defect today can acquire one (Atlas-Hermes, #5287 c61121). That
decay is the measurable with no clean precedent, and this harness records it.

WHAT THIS HARNESS ESTABLISHES, AND WHAT IT DOES NOT
---------------------------------------------------
It runs a *frozen verifier* — a deterministic decode-and-digest that does not
learn and shares no brain with any reader — over a dated fault set carrying two
representation classes (prose, escaped). It emits an append-only dated row so the
frozen verifier's stable pass and any *learned* reader's drift can be compared
across releases later.

It is single-model. It therefore probes the REPRESENTATION axis and the
FROZEN-VERIFIER arm only. It does NOT establish the different-weights arm, which
the paste names as the load-bearing one: "a different model API is not different
weights if both distill from the same two frontier teachers." A second reader on
genuinely different weights, in a withheld-answer cold seat, has to be supplied
externally. This harness refuses to print any different-weights conclusion, so a
future reader cannot mistake a single-model receipt for the two-reader claim.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAULTSET = ROOT / "scripts" / "eval_tasks" / "recoupling_faultset.json"
LEDGER = ROOT / "scripts" / "eval_tasks" / "recoupling_ledger.json"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_verifier(escaped_literal: str) -> str:
    """The non-learning arm: decode the escaped literal deterministically and digest it.

    Uses json.loads to resolve escape sequences (\\n, \\uXXXX, \\\\, \\") the same way
    every time, then hashes the code points. No model, no normalization, no idiom to
    drift into — this is the arm the paste says does not decay.
    """
    decoded = json.loads(f'"{escaped_literal}"')
    return _digest(decoded)


def set_digest(items: list[dict]) -> str:
    """A stable digest of the whole fault set, so a ledger row names the exact set."""
    payload = json.dumps(
        [(i["id"], i["representation_class"], i["escaped_literal"]) for i in items],
        ensure_ascii=True,
        sort_keys=True,
    )
    return _digest(payload)[:16]


def run_frozen_arm(items: list[dict]) -> tuple[int, int, list[str]]:
    """Return (passed, total, failures) for the frozen verifier against the canonical answers."""
    passed = 0
    failures: list[str] = []
    for it in items:
        expected = _digest(it["canonical"])
        got = frozen_verifier(it["escaped_literal"])
        if got == expected:
            passed += 1
        else:
            failures.append(it["id"])
    return passed, len(items), failures


def append_ledger_row(row: dict) -> None:
    ledger = {"_comment": "", "rows": []}
    if LEDGER.exists():
        ledger = json.loads(LEDGER.read_text())
    ledger["_comment"] = (
        "Append-only dated rows for the re-coupling harness. Each row is a receipt: "
        "(run date, set digest, set version, frozen-verifier pass rate, per-class n). "
        "The frozen arm should stay green forever (it does not learn); its value is as "
        "the fixed reference against which a supplied LEARNED reader's drift is read "
        "later. A learned-reader miss profile is NOT recorded here yet: single model, "
        "so the decorrelation that would decay cannot be measured against itself. "
        "Rows are evidence by their git history (external witness), not by a self-field."
    )
    ledger["rows"].append(row)
    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=True) + "\n")


def main() -> int:
    data = json.loads(FAULTSET.read_text())
    items = data["items"]

    passed, total, failures = run_frozen_arm(items)
    by_class: dict[str, int] = {}
    for it in items:
        by_class[it["representation_class"]] = by_class.get(it["representation_class"], 0) + 1

    if failures:
        raise RuntimeError(
            f"Frozen verifier failed on {failures} — the deterministic arm should decode "
            f"every canonical answer exactly. A broken frozen arm invalidates the receipt."
        )

    row = {
        "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "set_version": data["set_version"],
        "set_digest": set_digest(items),
        "frozen_verifier_pass": f"{passed}/{total}",
        "n_by_representation_class": by_class,
        "scope": "single-model: representation axis + frozen-verifier arm only; "
        "different-weights arm NOT established",
    }
    append_ledger_row(row)

    print(f"✓ frozen verifier: {passed}/{total} canonical answers decoded exactly")
    print(f"  set {row['set_digest']} (v{row['set_version']}), by class: {by_class}")
    print("  scope: single-model — representation + frozen-verifier only.")
    print("  NOT established: the different-weights cold-seat arm (needs an external reader).")
    print(f"  dated row appended to {LEDGER.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
