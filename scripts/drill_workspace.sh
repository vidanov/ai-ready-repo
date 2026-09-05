#!/usr/bin/env bash
# Source after setting REPO_ROOT. Re-exec the caller in a disposable copy.
# AI_READY_SANDBOX is an accidental-mutation guard, not a security boundary.
if [ "${AI_READY_SANDBOX:-}" != "$REPO_ROOT" ]; then
  exec uv run python -m ai_ready.verification.sandbox "$REPO_ROOT" \
    bash "scripts/$(basename "${BASH_SOURCE[1]}")" "$@"
fi
