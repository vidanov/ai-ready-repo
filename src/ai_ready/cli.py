"""Command line interface for inventory and reviewable adoption plans."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_ready.adoption import apply_plan, detect_stack, plan_adoption
from ai_ready.audit import audit
from ai_ready.verification.runner import verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assess and improve repository conventions")
    sub = parser.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("audit", help="Inspect configuration without running project code")
    inventory.add_argument("repo", type=Path, nargs="?", default=Path.cwd())
    inventory.add_argument("--json", action="store_true")
    check = sub.add_parser("verify", help="Execute the target repository's make verify")
    check.add_argument("repo", type=Path, nargs="?", default=Path.cwd())
    check.add_argument("--json", action="store_true")
    check.add_argument("--timeout", type=int, default=120)
    adopt = sub.add_parser("adopt", help="Preview a patch; use --apply to create new files")
    adopt.add_argument("repo", type=Path)
    adopt.add_argument("--stack")
    mode = adopt.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--detect", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.repo.is_dir():
            raise ValueError(f"Not a directory: {args.repo}")
        if args.command == "audit":
            report = audit(args.repo)
            print(json.dumps(report.to_dict(), indent=2) if args.json else report.render())
        elif args.command == "verify":
            receipt = verify(args.repo, args.timeout)
            if args.json:
                print(json.dumps(receipt.to_dict(), indent=2))
            else:
                print(receipt.stdout, end="")
                print(receipt.stderr, end="", file=sys.stderr)
                print(f"Evidence: {receipt.evidence}; passed: {receipt.passed}")
            return 0 if receipt.passed else 1
        elif args.detect:
            print("Detected: " + ", ".join(detect_stack(args.repo)))
        else:
            plan = plan_adoption(args.repo, args.stack)
            print(f"Stack: {plan.stack}")
            print(plan.diff() or "No new files proposed.")
            if args.apply:
                apply_plan(args.repo, plan)
                print(f"Created {len(plan.files)} files. Run the checks listed in ADOPTION.md.")
            else:
                print("Preview only. Use --apply to create these files.")
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
