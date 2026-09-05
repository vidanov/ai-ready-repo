#!/usr/bin/env python3
"""Compatibility entry point; run from a checkout or install the toolkit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_ready.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["audit", *sys.argv[1:]]))
