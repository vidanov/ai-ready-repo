#!/usr/bin/env bash
# Negative drill for the measurement-invalid gate (proposed on 1f916 #3539 by
# jerry c36960 + terry-synctzn c37020). Two-step falsifier:
#
#   1. Point a task's documented door at a guaranteed-missing executable.
#      Require the runner to classify it MEASUREMENT_INVALID (exit 127,
#      reachable=false) and NOT fold it into the pass/fail rate.
#   2. Restore the door. Require ran_passed.
#
# This proves two things a single pass rate cannot: that the gate can detect a
# corpse (a check that never ran), and that the recovery path is live. It is the
# executable form of the incident in CONTRIBUTING #031 — a dead check that read
# as "one task is hard" for four days because 127 and a real failure shared one
# bit.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TASK="scripts/eval_tasks/_drill_measurement_invalid.yaml"
cleanup() { rm -f "$TASK"; }
trap cleanup EXIT

echo "→ [1/2] Planting a task whose door is a guaranteed-missing command..."
cat > "$TASK" <<'YAML'
description: "drill: broken door must classify as measurement_invalid, not fail"
verification: "definitely_not_a_real_command_zzq"
expected_exit_code: 0
origin: birth
oracle_question: "does a missing door produce measurement_invalid disjoint from pass/fail?"
YAML

OUT="$(uv run python scripts/run_evals.py 2>&1)"

if ! echo "$OUT" | grep -q "MEASUREMENT_INVALID"; then
	echo "✗ drill-measurement-invalid FAILED: broken door was not classified measurement_invalid"
	echo "$OUT"
	exit 1
fi
if ! echo "$OUT" | grep -q "_drill_measurement_invalid: exit 127"; then
	echo "✗ drill-measurement-invalid FAILED: expected exit 127 for the missing command"
	echo "$OUT"
	exit 1
fi
# The corpse must NOT lower the rate: with two real tasks both passing, the
# rate must still read 2/2. If the invalid task were folded in, it would read
# 2/3.
if ! echo "$OUT" | grep -qE "Eval results: [0-9]+/[0-9]+ passed"; then
	echo "✗ drill-measurement-invalid FAILED: no rate line found"
	exit 1
fi
RATE_LINE="$(echo "$OUT" | grep -E "Eval results:" | head -1)"
if echo "$RATE_LINE" | grep -q "/3 passed"; then
	echo "✗ drill-measurement-invalid FAILED: corpse was counted in the denominator"
	echo "  $RATE_LINE"
	echo "  measurement_invalid must be disjoint from pass/fail (1f916 #3539)"
	exit 1
fi
echo "  ✓ broken door -> measurement_invalid, exit 127, excluded from the rate"

echo "→ [2/2] Restoring the door to a real command..."
cat > "$TASK" <<'YAML'
description: "drill: restored door must classify as ran_passed"
verification: "true"
expected_exit_code: 0
origin: birth
oracle_question: "does a working door produce ran_passed?"
YAML

OUT2="$(uv run python scripts/run_evals.py 2>&1)"
if echo "$OUT2" | grep -q "MEASUREMENT_INVALID"; then
	echo "✗ drill-measurement-invalid FAILED: restored door still read as measurement_invalid"
	echo "$OUT2"
	exit 1
fi
echo "  ✓ restored door -> ran and counted normally"

echo "✓ drill-measurement-invalid passed: the gate distinguishes a corpse from a failure and recovers"
