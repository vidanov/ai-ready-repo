#!/usr/bin/env bash
# Negative drill for the two-stage coverage gate (axiom-sovereign, 1f916 #3595).
# A scalar coverage floor measures HOW MANY runs were valid; it cannot see that
# the required DIMENSIONS for an object were exercised. This drill plants a task
# that declares a required axis (reason) but never exercises it — the command
# passes, but there is no expected_reason to check — and requires the runner to
# reject it as measurement_invalid, NOT average it into a healthy-looking rate.
#
# The required set is declared on the TASK, not the receipt, so the receipt
# cannot pass by silently omitting the axis. That is the circular escape hatch
# axiom-sovereign named, closed by construction.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TASK="scripts/eval_tasks/_drill_required_axis.yaml"
cleanup() { rm -f "$TASK"; }
trap cleanup EXIT

echo "→ [1/2] Planting a task that requires the 'reason' axis but never exercises it..."
cat > "$TASK" <<'YAML'
description: "drill: declares required reason axis but omits expected_reason"
verification: "true"
expected_exit_code: 0
required_axes: [reachability, reason]
origin: birth
oracle_question: "is a required-but-unexercised axis rejected, not scored green?"
YAML

set +e
OUT="$(uv run python scripts/run_evals.py --task _drill_required_axis 2>&1)"
set -e

# The command exits 0, so a naive runner would score this a pass. The gate must
# instead reject it: the reason axis was required but never exercised.
if ! echo "$OUT" | grep -qE "missing required axes .*reason"; then
	echo "✗ drill-required-axis FAILED: an unexercised required axis was not reported"
	echo "$OUT"
	exit 1
fi
if echo "$OUT" | grep -qE "1/1 passed"; then
	echo "✗ drill-required-axis FAILED: a task missing a required axis was scored as a pass"
	echo "$OUT"
	exit 1
fi
echo "  ✓ required-but-unexercised axis -> measurement_invalid, not a pass"

echo "→ [2/2] Exercising the axis (adding expected_reason)..."
cat > "$TASK" <<'YAML'
description: "drill: now exercises the reason axis"
verification: "echo DRILL_REASON_TAG"
expected_exit_code: 0
expected_reason: "DRILL_REASON_TAG"
required_axes: [reachability, reason]
origin: birth
oracle_question: "does exercising the required axis let the task be scored?"
YAML

set +e
OUT2="$(uv run python scripts/run_evals.py --task _drill_required_axis 2>&1)"
set -e
if echo "$OUT2" | grep -qE "missing required axes"; then
	echo "✗ drill-required-axis FAILED: axis was exercised but still reported missing"
	echo "$OUT2"
	exit 1
fi
echo "  ✓ exercised axis -> task is scored normally"

echo "✓ drill-required-axis passed: a required dimension that was never exercised is rejected, not averaged away"
