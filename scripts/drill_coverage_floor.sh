#!/usr/bin/env bash
# Negative drill for the measurement-coverage floor (raised on 1f916 #3539 by
# latex c37440 + jerry c37451). Disjointness (PR #42) pulls measurement_invalid
# out of the pass/fail denominator — correct, but on its own it lets the pass
# rate read 100% as the harness rots: nine corpses and one pass report 1/1.
#
# This drill reproduces latex's launder case: stack the run with broken-door
# tasks so the pass rate stays green (every task that DID run, passed) while
# coverage collapses below the floor. The runner must REFUSE the green rate —
# exit nonzero, name the coverage — instead of reporting a clean 100%.
#
# It is the original dead-check bug one level up: without this gate, the metric
# gets healthier as the instrument dies.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/scripts/drill_workspace.sh"
cd "$REPO_ROOT"

PLANTED=()
cleanup() {
	for f in "${PLANTED[@]}"; do rm -f "$f"; done
}
trap cleanup EXIT

echo "→ Planting broken-door tasks so coverage drops below the floor..."
# Every planted task's door is a guaranteed-missing command -> measurement_invalid.
# The real tasks in eval_tasks/ still pass, so the pass rate stays 100%. With
# enough corpses, coverage falls under 75% and the run must refuse the rate.
for i in 1 2 3 4 5; do
	TASK="scripts/eval_tasks/_drill_coverage_floor_${i}.yaml"
	PLANTED+=("$TASK")
	cat > "$TASK" <<YAML
description: "drill: corpse #${i} to sink coverage below the floor"
verification: "definitely_not_a_real_command_cov_${i}"
expected_exit_code: 0
origin: birth
oracle_question: "does a rotting harness get refused even when the pass rate is green?"
YAML
done

set +e
OUT="$(uv run python scripts/run_evals.py 2>&1)"
CODE=$?
set -e

# 1. The pass rate must still be green — this is the launder setup: every task
#    that actually ran, passed. If the rate were red, the drill would be testing
#    the wrong thing.
RATE_LINE="$(echo "$OUT" | grep -E "Eval results:" | head -1)"
if ! echo "$RATE_LINE" | grep -qE "\(100%\)"; then
	echo "✗ drill-coverage-floor FAILED: setup expected a 100% pass rate (the launder case)"
	echo "  $RATE_LINE"
	echo "$OUT"
	exit 1
fi
echo "  ✓ pass rate is green (100%) — the launder setup latex named"

# 2. Coverage must be reported, and below the floor.
if ! echo "$OUT" | grep -qE "Measurement coverage:"; then
	echo "✗ drill-coverage-floor FAILED: no coverage line reported"
	echo "$OUT"
	exit 1
fi
echo "  ✓ coverage reported next to the rate"

# 3. The run must REFUSE the green rate: nonzero exit + a coverage-floor message.
if [ "$CODE" -eq 0 ]; then
	echo "✗ drill-coverage-floor FAILED: run exited 0 over a rotting harness"
	echo "  a green rate below the coverage floor must not pass (1f916 #3539)"
	echo "$OUT"
	exit 1
fi
if ! echo "$OUT" | grep -qE "coverage .* below floor"; then
	echo "✗ drill-coverage-floor FAILED: nonzero exit but no coverage-floor reason"
	echo "$OUT"
	exit 1
fi
echo "  ✓ green rate refused: exit ${CODE}, coverage below floor named in the headline"

echo "✓ drill-coverage-floor passed: a 100% pass rate over a rotting harness is refused, not laundered"
