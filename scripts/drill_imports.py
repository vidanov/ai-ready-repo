"""Behavioral import-boundary drills. Called only in a disposable workspace."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def probe(source: str, dependency: str, permitted: bool) -> None:
    path = ROOT / "src" / Path(*source.split(".")) / "__init__.py"
    before = path.read_bytes()
    try:
        with path.open("a") as stream:
            stream.write(f"\nimport {dependency}\n")
        result = subprocess.run(
            ["lint-imports", "--no-cache"], capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        if permitted:
            if result.returncode != 0:
                raise RuntimeError(f"Legal edge {source} -> {dependency} rejected:\n{output}")
        elif not (
            result.returncode != 0
            and "BROKEN" in output
            and source in output
            and dependency in output
        ):
            raise RuntimeError(f"Forbidden edge {source} -> {dependency} not identified:\n{output}")
        print(
            f"Verified {'permitted' if permitted else 'forbidden'} edge: {source} -> {dependency}"
        )
    finally:
        path.write_bytes(before)


def main() -> int:
    if os.environ.get("AI_READY_SANDBOX") != str(ROOT):
        raise RuntimeError("Run this drill through ai_ready.verification.sandbox")
    mode = sys.argv[1]
    if mode == "deny":
        for source, dependency in (
            ("domain", "infrastructure"),
            ("domain", "application"),
            ("application", "infrastructure"),
        ):
            probe(f"ai_ready_repo.{source}", f"ai_ready_repo.{dependency}", False)
        probe("ai_ready", "ai_ready_repo", False)
    elif mode == "permit":
        for source, dependency in (
            ("application", "domain"),
            ("infrastructure", "application"),
            ("infrastructure", "domain"),
        ):
            probe(f"ai_ready_repo.{source}", f"ai_ready_repo.{dependency}", True)
    elif mode == "reason":
        probe("ai_ready_repo.domain", "ai_ready_repo.infrastructure", False)
        path = ROOT / "src/ai_ready_repo/domain/__init__.py"
        with path.open("a") as stream:
            stream.write("\nthis is not valid python\n")
        result = subprocess.run(
            ["lint-imports", "--no-cache"], capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or "BROKEN" in output:
            raise RuntimeError(f"Syntax error was not distinguished from a broken edge:\n{output}")
        print("Syntax failure distinguished from import-boundary failure")
    else:
        raise ValueError(f"Unknown drill: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
