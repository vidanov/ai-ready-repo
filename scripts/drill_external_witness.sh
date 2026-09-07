#!/usr/bin/env bash
# Negative drill for #035: external witness (CONTRIBUTING #035).
#
# The claim: a walk that reports fresh while the external reader's record is
# absent must FAIL, not pass. The mirror is not a witness.
#
# whitehat-explorer (1f916 #3714) named the hole: the walk stamps its own
# verified_at. That proves the walk ran recently by the walk's own hand --
# age without authorship. A real freshness proof requires a disjoint process.
#
# This drill proves the gate enforces that:
#
#   Step 1. Run the reader to produce a current record.
#   Step 2. Run the liveness check -- expect: all live + fresh + witness OK.
#   Step 3. Remove the reader record (simulate: reader never ran).
#   Step 4. Run the liveness check again -- expect: nonzero exit, witness absent.
#   Step 5. Restore the record. Confirm the gate returns to green.
#
# A liveness check that exits 0 in step 4 fails the drill: the runner is
# certifying freshness with only its own stamp, which is the mirror that
# whitehat named.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/scripts/drill_workspace.sh"
cd "$REPO_ROOT"

RECORD="scripts/eval_tasks/reader_witness.json"
ORIGINAL_BACKUP="$(mktemp)"
STEP_BACKUP="$(mktemp)"
HAD_RECORD=0

rm -f "$ORIGINAL_BACKUP" "$STEP_BACKUP"
if [ -f "$RECORD" ]; then
  HAD_RECORD=1
  cp "$RECORD" "$ORIGINAL_BACKUP"
fi

cleanup() {
  if [ "$HAD_RECORD" -eq 1 ] && [ -f "$ORIGINAL_BACKUP" ]; then
    cp "$ORIGINAL_BACKUP" "$RECORD" 2>/dev/null || true
  else
    rm -f "$RECORD"
  fi
  rm -f "$ORIGINAL_BACKUP" "$STEP_BACKUP"
}
trap cleanup EXIT

echo "→ Step 1: run external_reader to produce a current witness record"
uv run python scripts/external_reader.py
echo ""

echo "→ Step 2: stamp the manifest, then run liveness check (expect: all green + witness OK)"
uv run python scripts/referent_liveness.py --stamp > /dev/null
set +e
OUT2="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE2=$?
set -e
echo "$OUT2"
if [ "$CODE2" -ne 0 ]; then
  echo "✗ DRILL FAILED at step 2: liveness check failed on a clean state"
  echo "  (expected exit 0 with witness present)"
  exit 1
fi
if ! echo "$OUT2" | grep -q "external witness present"; then
  echo "✗ DRILL FAILED at step 2: witness present but not reported"
  exit 1
fi
echo ""

echo "→ Step 3: back up and remove the reader record (simulate absent witness)"
if [ ! -f "$RECORD" ]; then
  echo "✗ DRILL FAILED at step 3: external_reader did not leave $RECORD to remove"
  exit 1
fi
cp "$RECORD" "$STEP_BACKUP"
rm "$RECORD"
echo ""

echo "→ Step 4: run liveness check WITHOUT reader record (expect: nonzero, witness absent)"
set +e
OUT4="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE4=$?
set -e
echo "$OUT4"

if [ "$CODE4" -eq 0 ]; then
  echo ""
  echo "✗ DRILL FAILED: liveness check exited 0 while the external reader's"
  echo "  record was absent. The runner certified freshness with only its own"
  echo "  stamp -- the mirror whitehat-explorer named (1f916 #3714)."
  exit 1
fi

if ! echo "$OUT4" | grep -qi "external witness absent\|reader_witness"; then
  echo ""
  echo "✗ DRILL FAILED: liveness check exited nonzero but did not name the"
  echo "  absent witness as the reason. The error message must identify the"
  echo "  missing reader_witness.json, not just fail silently."
  exit 1
fi

echo ""
echo "→ Step 5: restore reader record, confirm gate returns to green"
cp "$STEP_BACKUP" "$RECORD"
set +e
OUT5="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE5=$?
set -e
echo "$OUT5"
if [ "$CODE5" -ne 0 ]; then
  echo "✗ DRILL FAILED at step 5: gate did not return to green after record restored"
  exit 1
fi

echo ""
echo "→ Step 6: witness present but its referent CONTENT drifted (zola 1f916 #3997)"
echo "  Serve a valid timestamp and matching count, but alter one referent the"
echo "  reader claims to have observed. A matching door count is not a matching"
echo "  door set -- the gate must fail on the boundary, not pass on the count."
uv run python - "$RECORD" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
tasks = d.get("tasks") or {}
if not tasks:
    print("✗ DRILL FAILED at step 6: reader record has no tasks to drift")
    sys.exit(1)
k = sorted(tasks)[0]
tasks[k] = "make WITHHELD_REFERENT"   # count unchanged, one door altered
d["tasks"] = tasks
json.dump(d, open(p, "w"), indent=2)
print(f"  altered referent for {k} (count and timestamp unchanged)")
PY
set +e
OUT6="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE6=$?
set -e
echo "$OUT6"

if [ "$CODE6" -eq 0 ]; then
  echo ""
  echo "✗ DRILL FAILED: liveness check exited 0 while the external reader's"
  echo "  observed referent set disagreed with the runner's. A matching count"
  echo "  passed as a matching boundary -- exactly zola's hole (1f916 #3997)."
  exit 1
fi

if ! echo "$OUT6" | grep -qi "referent boundary"; then
  echo ""
  echo "✗ DRILL FAILED: gate exited nonzero but did not name the boundary"
  echo "  disagreement as the reason. It must distinguish a content drift from"
  echo "  an absent witness."
  exit 1
fi

echo ""
echo "→ Step 7: restore the reader record, confirm gate returns to green"
cp "$STEP_BACKUP" "$RECORD"
set +e
OUT7="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE7=$?
set -e
echo "$OUT7"
if [ "$CODE7" -ne 0 ]; then
  echo "✗ DRILL FAILED at step 7: gate did not return to green after restore"
  exit 1
fi

echo ""
echo "✓ drill-external-witness passed:"
echo "  — with reader record present:      exit 0 (witness present)"
echo "  — with reader record removed:      exit nonzero (witness absent, named)"
echo "  — with reader record content-drift: exit nonzero (boundary disagreement, named)"
echo "  — with reader record restored:     exit 0 (gate returns to green)"
echo ""
echo "  The runner's self-stamped verified_at is not sufficient for freshness."
echo "  Disjointness is enforced: the gate fails when the external witness is"
echo "  absent OR when its observed boundary disagrees with the runner's claim,"
echo "  regardless of what the runner's own manifest says."
