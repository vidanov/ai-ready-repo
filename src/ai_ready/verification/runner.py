"""Execute the documented verification entry point and retain its evidence."""

from __future__ import annotations

import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ai_ready.verification.process import run


@dataclass(frozen=True)
class Receipt:
    root: str
    command: tuple[str, ...]
    evidence: str
    exit_code: int | None
    elapsed_seconds: float
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.evidence == "executed" and self.exit_code == 0

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "passed": self.passed}


def verify(root: Path, timeout: int = 120) -> Receipt:
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    command = ("make", "verify")
    start = time.monotonic()
    try:
        result = run(command, cwd=root, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        output = error.stdout if isinstance(error, subprocess.TimeoutExpired) else ""
        detail = error.stderr if isinstance(error, subprocess.TimeoutExpired) else ""
        return Receipt(
            str(root.resolve()),
            command,
            "unknown",
            None,
            round(time.monotonic() - start, 3),
            output if isinstance(output, str) else "",
            (detail if isinstance(detail, str) else "") + str(error),
        )
    return Receipt(
        str(root.resolve()),
        command,
        "executed",
        result.returncode,
        round(time.monotonic() - start, 3),
        result.stdout,
        result.stderr,
    )
