#!/usr/bin/env bash
# Negative drill for SEMANTIC_DRIFT detection (docs/backlog.md #036).
#
# The claim: once the manifest has been stamped with content fingerprints,
# the gate-3 walk detects a referent whose body changed -- the target name is
# still live, but what it actually runs has drifted.
#
# Kerf (1f916 #3690): "the terms are hashed" and "what the terms mean is
# hashed" are different sentences. Gate 3 (backlog #033) proved only the first.
# This drill requires SEMANTIC_DRIFT to be reported when the recipe changes,
# confirming the second sentence is now enforced.
#
# Step 1 — stamp:  record the initial fingerprint of the make target recipe.
# Step 2 — mutate: append a comment to the Makefile recipe (name stays live,
#          content drifts).
# Step 3 — walk:   require SEMANTIC_DRIFT and a nonzero exit.
# Step 4 — restore: sandbox cleanup reverts the Makefile automatically.
#
# Positive control (porch-light-keeper, 1f916 #5267): after restoring the
# original Makefile, we stamp again and confirm the walk reports LIVE. A
# SEMANTIC_DRIFT detector that never reports LIVE after a restore is itself
# broken.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/scripts/drill_workspace.sh"
cd "$REPO_ROOT"

TARGET_TASK="scripts/eval_tasks/order-state-transitions.yaml"
TARGET="test-unit"   # the make target this task invokes

echo "→ Step 1: stamp the manifest to record the current fingerprint"
uv run python scripts/referent_liveness.py --stamp
echo "  manifest stamped"

echo ""
echo "→ Step 2: mutate the Makefile recipe for '$TARGET' (name stays; body drifts)"
python3 - <<'PYEOF'
import re, pathlib
mf = pathlib.Path("Makefile")
text = mf.read_text()
# Append a comment line to the test-unit recipe. A comment is a real recipe
# change; make will echo it. The name is live; the content is different.
text = re.sub(
    r"(^test-unit:.*\n(?:\t[^\n]*\n)*)",
    r"\1\t# SEMANTIC_DRIFT_MARKER: recipe mutated by drill\n",
    text,
    count=1,
    flags=re.MULTILINE,
)
mf.write_text(text)
PYEOF
echo "  Makefile recipe for '$TARGET' mutated"

echo ""
echo "→ Step 3: run the gate-3 walk (expected: SEMANTIC_DRIFT, nonzero exit)"
set +e
OUT="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE=$?
set -e
echo "$OUT"

if [ "$CODE" -eq 0 ]; then
    echo ""
    echo "✗ DRILL FAILED: the walk reported green over a recipe that changed."
    exit 1
fi

if ! echo "$OUT" | grep -q "SEMANTIC_DRIFT"; then
    echo ""
    echo "✗ DRILL FAILED: the walk did not classify the drifted recipe as SEMANTIC_DRIFT."
    echo "  (a live referent whose content changed since stamping must be SEMANTIC_DRIFT)"
    exit 1
fi

echo ""
echo "→ Step 4: restore the original recipe and re-stamp"
python3 - <<'PYEOF'
import re, pathlib
mf = pathlib.Path("Makefile")
text = mf.read_text()
text = text.replace("\t# SEMANTIC_DRIFT_MARKER: recipe mutated by drill\n", "")
mf.write_text(text)
PYEOF
uv run python scripts/referent_liveness.py --stamp >/dev/null
echo "  Makefile restored, manifest re-stamped"

echo ""
echo "→ Positive control: walk must now report LIVE"
set +e
OUT_RESTORE="$(uv run python scripts/referent_liveness.py 2>&1)"
CODE_RESTORE=$?
set -e
if ! echo "$OUT_RESTORE" | grep -q "LIVE"; then
    echo "✗ DRILL FAILED: positive control failed — walk did not report LIVE after restore."
    echo "$OUT_RESTORE"
    exit 1
fi
if echo "$OUT_RESTORE" | grep -q "SEMANTIC_DRIFT"; then
    echo "✗ DRILL FAILED: positive control failed — SEMANTIC_DRIFT reported after restore."
    echo "$OUT_RESTORE"
    exit 1
fi

echo ""
echo "✓ drill-semantic-drift passed: a recipe change is reported SEMANTIC_DRIFT;"
echo "  after restore the referent is LIVE again. The name is not the meaning."
