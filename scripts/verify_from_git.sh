#!/usr/bin/env bash
# Git-sourced verification: run the unit tests from the committed copy at
# HEAD, not from the working tree. This closes the gap that verify_tamperproof
# leaves open (see CONTRIBUTING.md #030): its trusted copy is taken from the
# live working tree at run time, so a same-session edit to a test file DOES
# reach the "trusted" copy. Sourcing from git history puts the checker behind
# a boundary the working-tree editor cannot cross without committing.
#
# The axis that matters (credit: hermes-voyager, 1f916 #3385): not verbal-vs-
# structural enforcement, but whether the thing that verifies sits inside or
# outside the checked party's write path. `git show HEAD:...` reads bytes the
# agent cannot alter without a commit, which is a recorded, reviewable act.
#
# LIMITATION: an agent that commits a weakened test to HEAD defeats this too.
# The boundary is "uncommitted working-tree edits", not "all edits". Full
# protection needs the checker off the machine entirely (CI on a runner with
# no agent shell, branch protection enforced by the forge). This is one rung
# up the ladder from verify_tamperproof, not the top of it.
#
# Usage:
#   bash scripts/verify_from_git.sh [git-ref]
# Default ref: HEAD

set -euo pipefail

REF="${1:-HEAD}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TRUSTED_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TRUSTED_DIR"; }
trap cleanup EXIT

cd "$REPO_ROOT"

echo "→ Extracting unit tests from git ref '$REF' (not the working tree)..."

# List the test files tracked at REF, extract each from git history.
mkdir -p "$TRUSTED_DIR/tests/unit"
git ls-tree -r --name-only "$REF" -- tests/unit \
  | grep -E '\.py$' \
  | while read -r f; do
      dest="$TRUSTED_DIR/$f"
      mkdir -p "$(dirname "$dest")"
      git show "$REF:$f" > "$dest"
    done

echo "→ Trusted tests extracted from $REF at $TRUSTED_DIR"
echo "→ Running unit tests from the committed copy against working src/..."

# Tests come from git; source under test comes from the working tree. That is
# deliberate: we are verifying the CODE the agent wrote, using the TESTS the
# agent cannot have silently weakened in this session.
uv run --project "$REPO_ROOT" pytest "$TRUSTED_DIR/tests/unit" \
  --cov="$REPO_ROOT/src" --cov-report=term-missing -q

echo ""
echo "✓ Git-sourced verification passed (tests from $REF, code from working tree)"
