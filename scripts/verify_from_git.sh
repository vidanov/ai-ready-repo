#!/usr/bin/env bash
# Use acceptance tests and pytest configuration from an explicitly chosen ref.
# HEAD protects against uncommitted test edits only. A stronger caller pins a
# reviewed ref and invokes this verifier from outside the candidate write path.
# This script is not an OS sandbox or a substitute for hosted branch protection.
set -euo pipefail
REF="${1:-HEAD}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TRUSTED_DIR="$(mktemp -d)"
trap 'rm -rf "$TRUSTED_DIR"' EXIT
cd "$REPO_ROOT"
REVISION="$(git rev-parse --verify "$REF^{commit}")"
echo "Acceptance tests and configuration from $REVISION; implementation from working tree"
git show "$REVISION:pyproject.toml" > "$TRUSTED_DIR/pyproject.toml"
mkdir -p "$TRUSTED_DIR/tests"
git ls-tree -r --name-only "$REVISION" -- tests/unit | while IFS= read -r file; do
  mkdir -p "$TRUSTED_DIR/$(dirname "$file")"
  git show "$REVISION:$file" > "$TRUSTED_DIR/$file"
done
# Tests which import scripts by relative path must exercise the candidate
# implementation, not an old copy of that implementation from the trusted ref.
cp -R "$REPO_ROOT/scripts" "$TRUSTED_DIR/scripts"
export PYTHONPATH="$REPO_ROOT/src:$TRUSTED_DIR${PYTHONPATH:+:$PYTHONPATH}"
# Coverage belongs to normal verification. Historical acceptance suites need
# not cover modules added after their trusted revision.
uv run --project "$REPO_ROOT" pytest -c "$TRUSTED_DIR/pyproject.toml" \
  "$TRUSTED_DIR/tests/unit" --no-cov -q
echo "Git-sourced acceptance checks passed ($REVISION)"
