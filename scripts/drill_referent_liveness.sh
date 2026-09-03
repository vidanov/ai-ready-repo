#!/usr/bin/env bash
# Negative drill for gate 3, referent liveness (CONTRIBUTING #033, kilmon-ai
# 1f916 #3357 c37040). The claim: the manifest walk detects a referent that
# has drifted out from under a fixture -- the #031 class, where a task stayed
# green over `python` (exit 127) because textual agreement held while the
# thing it pointed at was gone.
#
# This drill plants exactly that: it rewrites a task's `verification` to name a
# script that does not exist, then requires the walk to report STALE_OR_DRIFTED
# and exit nonzero. A walk that reports green over a dead referent fails the
# drill. It is the dead-check bug reproduced against the checker built to catch
# it.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TASK="scripts/eval_tasks/order-state-transitions.yaml"
BACKUP="$(mktemp)"
cp "$TASK" "$BACKUP"

cleanup() {
  cp "$BACKUP" "$TASK"
  rm -f "$BACKUP"
}
trap cleanup EXIT

echo "→ Planting a drifted referent: point the task at a script that is gone"
# Rewrite the verification line to a script path that does not exist. The
# referent FORM is recognized (a python invocation), so the correct verdict is
# STALE_OR_DRIFTED, not REFERENT_MISMATCH.
python3 - "$TASK" <<'PYEOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
text = re.sub(
    r'^verification:.*$',
    'verification: "uv run python scripts/eval_tasks/gone_moved_away.py"',
    text,
    count=1,
    flags=re.M,
)
open(path, "w").write(text)
PYEOF

echo "→ Running the gate-3 walk (expected: STALE_OR_DRIFTED, nonzero exit)"
set +e
OUT="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE=$?
set -e
echo "$OUT"

if [ "$CODE" -eq 0 ]; then
  echo "✗ DRILL FAILED: the walk reported green over a drifted referent."
  exit 1
fi

if ! echo "$OUT" | grep -q "STALE_OR_DRIFTED"; then
  echo "✗ DRILL FAILED: the walk did not classify the dead referent as STALE_OR_DRIFTED."
  echo "  (a recognized referent form whose target is gone must be STALE, not MISMATCH)"
  exit 1
fi

echo "✓ drill-referent-liveness passed: a referent that drifted out from under"
echo "  its fixture is reported STALE_OR_DRIFTED and refused, not scored green."
