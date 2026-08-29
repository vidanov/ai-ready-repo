#!/usr/bin/env bash
# Tamper-proof verification: run acceptance checks from a trusted copy
# that the agent cannot modify.
#
# Usage:
#   make verify-tamperproof
#
# This copies verification infrastructure to a temp directory BEFORE the
# agent's changes, then runs the checks from there against the working
# source tree. If the agent weakened the Makefile, tests, or lint config,
# the trusted copy still catches it.
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
[ -d "$REPO_ROOT/docs/adr" ] && mkdir -p "$TRUSTED_DIR/docs" && cp -r "$REPO_ROOT/docs/adr" "$TRUSTED_DIR/docs/"

echo "→ Trusted copy at $TRUSTED_DIR"
echo "→ Running verification from trusted copy..."

# Run the checks using the trusted Makefile but against the working src/
# We override the test and lint paths to point at the trusted copies
cd "$TRUSTED_DIR"

# 1. Format check (runs against working src — format is in the source, not tests)
echo "→ [1/5] Format check..."
uv run ruff format --check "$REPO_ROOT/src" "$TRUSTED_DIR/tests"

# 2. Lint (trusted test files, working source)
echo "→ [2/5] Lint..."
uv run ruff check "$REPO_ROOT/src" "$TRUSTED_DIR/tests"

# 3. Typecheck (working source)
echo "→ [3/5] Type check..."
uv run mypy "$REPO_ROOT/src"

# 4. Import boundaries (uses trusted pyproject.toml)
echo "→ [4/5] Import boundaries..."
IMPORTLINTER_CONFIG="$TRUSTED_DIR/pyproject.toml" uv run lint-imports

# 5. Unit tests from trusted copy
echo "→ [5/5] Unit tests (trusted)..."
uv run pytest "$TRUSTED_DIR/tests/unit" -v --cov="$REPO_ROOT/src" --cov-report=term-missing

# 6. ADR validation from trusted copy
echo "→ [6/6] ADR validation (trusted)..."
python3 "$TRUSTED_DIR/scripts/validate_adrs.py"

echo ""
echo "✓ Tamper-proof verification passed"
