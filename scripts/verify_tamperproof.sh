#!/usr/bin/env bash
# Tamper-proof verification: run acceptance checks from a copy of the
# verification files (Makefile, tests, scripts, ADRs), separate from
# whatever copy an agent has open in an editor or is mid-edit on.
#
# Usage:
#   make verify-tamperproof
#
# LIMITATION: the copy is taken at run time, from the current working
# tree — not from a prior commit or a pre-session snapshot. If the tests
# or lint config were already weakened *before* this command runs, this
# catches nothing; it only protects against tampering that happens
# concurrently with, or attempted after, this specific invocation. Real
# protection against a prior-committed weakening needs the trusted copy
# sourced from git history (e.g. a pinned ref or the last commit on
# main) instead of the live working tree — see CONTRIBUTING.md #030.
#
# See docs/FIXTURES.md F-003 for the design rationale.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TRUSTED_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TRUSTED_DIR"; }
trap cleanup EXIT

echo "→ Copying verification files to trusted directory..."

# Copy the files an agent might tamper with
cp "$REPO_ROOT/Makefile" "$TRUSTED_DIR/"
cp "$REPO_ROOT/pyproject.toml" "$TRUSTED_DIR/"
cp -r "$REPO_ROOT/tests" "$TRUSTED_DIR/"
cp -r "$REPO_ROOT/scripts" "$TRUSTED_DIR/"
# ruff's first-party import detection (isort) walks up from the linted path
# looking for a src/ layout next to pyproject.toml. Without src/ here, it
# misclassifies ai_ready_repo imports as third-party. Copy src/ so config
# discovery matches the real project; the actual checks below still target
# $REPO_ROOT/src, not this copy.
cp -r "$REPO_ROOT/src" "$TRUSTED_DIR/"
[ -d "$REPO_ROOT/docs/adr" ] && mkdir -p "$TRUSTED_DIR/docs" && cp -r "$REPO_ROOT/docs/adr" "$TRUSTED_DIR/docs/"

echo "→ Trusted copy at $TRUSTED_DIR"
echo "→ Running verification from trusted copy..."

# Run the checks using the trusted Makefile but against the working src/
# We override the test and lint paths to point at the trusted copies.
# --project "$REPO_ROOT": TRUSTED_DIR has no src/, so `uv run` must resolve
# and build against the real project (which has src/) rather than trying to
# build a package out of the temp dir's partial copy.
cd "$TRUSTED_DIR"

# 1. Format check (runs against working src — format is in the source, not tests)
echo "→ [1/5] Format check..."
uv run --project "$REPO_ROOT" ruff format --check "$REPO_ROOT/src" "$TRUSTED_DIR/tests"

# 2. Lint (trusted test files, working source)
echo "→ [2/5] Lint..."
uv run --project "$REPO_ROOT" ruff check "$REPO_ROOT/src" "$TRUSTED_DIR/tests"

# 3. Typecheck (working source)
echo "→ [3/5] Type check..."
uv run --project "$REPO_ROOT" mypy "$REPO_ROOT/src"

# 4. Import boundaries (uses trusted pyproject.toml)
echo "→ [4/5] Import boundaries..."
IMPORTLINTER_CONFIG="$TRUSTED_DIR/pyproject.toml" uv run --project "$REPO_ROOT" lint-imports

# 5. Unit tests from trusted copy
echo "→ [5/5] Unit tests (trusted)..."
uv run --project "$REPO_ROOT" pytest "$TRUSTED_DIR/tests/unit" -v --cov="$REPO_ROOT/src" --cov-report=term-missing

# 6. ADR validation from trusted copy
echo "→ [6/6] ADR validation (trusted)..."
python3 "$TRUSTED_DIR/scripts/validate_adrs.py"

echo ""
echo "✓ Tamper-proof verification passed"
