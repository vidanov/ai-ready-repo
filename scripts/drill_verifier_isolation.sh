#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/scripts/drill_workspace.sh"
cd "$REPO_ROOT"

# The sandbox baseline contains the original tests. A planted failing test
# must be visible to working-tree pytest and invisible to the ref-sourced run.
cat >> tests/unit/test_domain_order.py <<'PY'

def test_planted_failure() -> None:
    assert False, "PLANTED_WORKING_TREE_TEST"
PY
set +e
CONTROL="$(uv run pytest tests/unit/test_domain_order.py -k test_planted_failure --no-cov 2>&1)"
CODE=$?
set -e
if [ "$CODE" -ne 1 ] || ! echo "$CONTROL" | grep -q PLANTED_WORKING_TREE_TEST; then
  echo "Control did not execute the planted failure"
  echo "$CONTROL"
  exit 1
fi
bash scripts/verify_from_git.sh HEAD
echo "Verified: working-tree test fails; committed tests ignore the plant."
