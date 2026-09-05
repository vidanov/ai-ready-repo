"""Copy a candidate workspace before running a mutation drill.

This isolates accidental file changes; it is not an OS security sandbox.
Drill commands remain trusted code with the invoking user's permissions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ai_ready.verification.process import run


def run_isolated(
    root: Path, command: list[str], timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="ai-ready-drill-") as temporary:
        workspace = (Path(temporary) / "repo").resolve()
        shutil.copytree(
            root,
            workspace,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
                ".*cache*",
                ".coverage*",
                "htmlcov",
                "dist",
                "build",
                ".env",
                "cdk.out",
                ".terraform",
            ),
        )
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(
            {
                "AI_READY_SANDBOX": str(workspace),
                "PYTHONPATH": str(workspace / "src"),
                "UV_PROJECT_ENVIRONMENT": sys.prefix,
                "UV_NO_SYNC": "1",
                "PATH": str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }
        )
        # A local baseline makes diff-sensitive evals independent of the user's
        # uncommitted changes and supports the verifier-isolation drill.
        for args in (
            ["git", "init", "-q"],
            ["git", "add", "."],
            [
                "git",
                "-c",
                "user.name=Drill",
                "-c",
                "user.email=drill@example.invalid",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "Disposable drill baseline",
            ],
        ):
            subprocess.run(
                args, cwd=workspace, env=env, check=True, capture_output=True, timeout=30
            )
        return run(command, cwd=workspace, env=env, timeout=timeout)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python -m ai_ready.verification.sandbox ROOT COMMAND [ARGS]", file=sys.stderr)
        return 2
    try:
        result = run_isolated(Path(sys.argv[1]), sys.argv[2:])
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Drill could not execute: {error}", file=sys.stderr)
        return 2
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
