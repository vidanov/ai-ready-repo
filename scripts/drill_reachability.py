"""Drill: prove the guard-reachability check fires on a planted status write.

A check that has never rejected a real violation cannot be told apart from a
check that is unreachable (porch-light-keeper, 1f916 #5267; concept
docs/research/foreign-fault-corpus.md). This drill plants a direct write to
`order._status` in a non-domain source file, runs check_reachability.py, and
asserts it convicts. Runs in a disposable workspace via the sandbox module so
the planted fault never touches the real checkout.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if os.environ.get("AI_READY_SANDBOX") != str(ROOT):
        raise RuntimeError("Run this drill through ai_ready.verification.sandbox")

    # A non-domain file the check scans. Application layer is scanned; domain is exempt.
    target = ROOT / "src" / "ai_ready_repo" / "application" / "__init__.py"
    before = target.read_bytes()
    try:
        with target.open("a") as stream:
            stream.write(
                "\n\ndef _planted_bypass(order: object) -> None:\n"
                "    order._status = 'delivered'  # planted: bypasses transition()\n"
            )
        result = subprocess.run(
            ["uv", "run", "python3", "scripts/check_reachability.py"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            raise RuntimeError(
                f"check_reachability.py passed on a planted status write — check is "
                f"unreachable or blind:\n{output}"
            )
        if "_status" not in output or "application" not in output:
            raise RuntimeError(f"check fired but did not name the planted violation:\n{output}")
        print("✓ drill-reachability passed: check convicted the planted status bypass")
    finally:
        target.write_bytes(before)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
