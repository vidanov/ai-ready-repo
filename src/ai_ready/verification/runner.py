"""Execute the documented verification entry point and retain its evidence."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ai_ready.verification.process import run

# A Makefile target definition: name at line start, before the first colon.
# Used to confirm `verify` is a real recipe, not an incidental file that make
# would report "Nothing to be done" for. Without this guard, a directory holding
# a plain file named `verify` and no Makefile makes `make verify` exit 0, which
# the runner would otherwise read as a pass -- a dead check (F-004) in the
# toolkit itself: verification success with nothing verified.
_MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.-]+)\s*:", re.MULTILINE)


def _defines_verify_target(root: Path) -> bool:
    """True iff a Makefile in root declares a `verify` target."""
    for name in ("Makefile", "makefile", "GNUmakefile"):
        path = root / name
        if path.is_file():
            try:
                text = path.read_text()
            except OSError:
                return False
            return "verify" in _MAKE_TARGET.findall(text)
    return False


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
    command = ("make", "--no-print-directory", "verify")
    start = time.monotonic()
    # Guard against the dead-check case: with no Makefile `verify` target, an
    # incidental file named `verify` makes `make verify` exit 0 ("Nothing to be
    # done"), which is not evidence anything ran. Missing verification
    # configuration is `unknown` (measurement_invalid), never a pass.
    if not _defines_verify_target(root):
        return Receipt(
            str(root.resolve()),
            command,
            "unknown",
            None,
            round(time.monotonic() - start, 3),
            "",
            "no Makefile `verify` target: verification configuration is missing, "
            "so `make verify` exiting 0 would not mean any check ran",
        )
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
