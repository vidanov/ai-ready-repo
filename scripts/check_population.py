"""Compare the actual verify prerequisite graph with explicit evaluation coverage.

This checks declared coverage, not whether a test can detect every defect. The
surface comes from Makefile, independently of the task files. Only literal rules
and plain make invocations are supported; unsupported reachable syntax fails.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def graph(text: str) -> dict[str, set[str]]:
    rules: dict[str, set[str]] = {}
    for line in text.splitlines():
        match = re.match(r"^([\w-]+):([^#]*)", line)
        if match:
            rules.setdefault(match[1], set()).update(match[2].split())
    return rules


def closure(rules: dict[str, set[str]], targets: set[str]) -> set[str]:
    seen: set[str] = set()
    pending = list(targets)
    while pending:
        target = pending.pop()
        if target in seen:
            continue
        if target not in rules:
            raise ValueError(f"undefined target or unsupported prerequisite: {target}")
        seen.add(target)
        pending.extend(rules[target] - seen)
    return seen


def check(root: Path) -> list[str]:
    rules = graph((root / "Makefile").read_text())
    surface = closure(rules, {"verify"}) - {"verify"}
    if not surface:
        raise ValueError("verify has no prerequisite checks")
    tasks = sorted((root / "scripts/eval_tasks").glob("*.yaml"))
    if not tasks:
        raise ValueError("no evaluation tasks found")
    covered: set[str] = set()
    for path in tasks:
        task = yaml.safe_load(path.read_text())
        if not isinstance(task, dict):
            raise ValueError(f"{path.name}: expected task mapping")
        claims = task.get("covers", [])
        if not isinstance(claims, list) or any(not isinstance(t, str) for t in claims):
            raise ValueError(f"{path.name}: covers must be a list of target names")
        if not claims:
            continue
        command = task.get("verification")
        if not isinstance(command, str):
            raise ValueError(f"{path.name}: missing verification command")
        tokens = shlex.split(command)
        if len(tokens) < 2 or tokens[0] != "make":
            raise ValueError(f"{path.name}: coverage requires a plain make invocation")
        reached = closure(rules, set(tokens[1:]))
        for target in claims:
            if target not in surface or target not in reached:
                raise ValueError(f"{path.name}: {target} is not a reachable verification check")
        covered.update(claims)
    return sorted(surface - covered)


def main(root: Path = ROOT) -> int:
    try:
        missing = check(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"MEASUREMENT_INVALID: {exc}")
        return 3
    if missing:
        print("REFERENT_UNAUTHORED: no evaluation coverage declared for " + ", ".join(missing))
        return 1
    print("Verification population covered; declarations checked, task commands not executed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
