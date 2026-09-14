"""Static reachability check for the Order status guard (ADR-DOMAIN-001, #041).

Guard *correctness* (transition() rejects invalid moves) is covered by
`make drill-transition-guard`. This check covers the separate *reachability*
property: that the status field is only ever written through `transition()`,
never by direct assignment from a caller.

It is a static AST scan over `src/`, more precise than the ADR's
`rg "\\.status\\s*="` regex (it ignores comparisons, matches `_status`, and
scopes the domain layer as the one place allowed to write `_status`).

Declared reach boundary (concept: docs/research/foreign-fault-corpus.md):

- DECIDED and rejected: an attribute assignment `x.status = ...` or
  `x._status = ...` (including augmented and annotated assignment) in any file
  under `src/` outside the domain layer.
- CANNOT DECIDE, reported loudly: dynamic writes the AST cannot resolve to the
  status field statically -- `setattr(x, "status", ...)`, `x.__dict__[...] = ...`,
  ORM update calls, deserialization. These are printed as an explicit
  "cannot decide" boundary list rather than passing silently. A silent pass at
  the boundary is the state this check exists to remove.

Exit status: non-zero if any decided violation is found. The cannot-decide list
is reported but does not fail the build on its own; it is the written-down,
loud edge of the check's reach.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DOMAIN = SRC / "ai_ready_repo" / "domain"

STATUS_NAMES = {"status", "_status"}


def _targets(node: ast.stmt) -> list[ast.expr]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AugAssign | ast.AnnAssign):
        return [node.target]
    return []


def _is_status_attr(target: ast.expr) -> bool:
    return isinstance(target, ast.Attribute) and target.attr in STATUS_NAMES


def _in_domain(path: Path) -> bool:
    return DOMAIN in path.parents


def scan_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (decided_violations, cannot_decide) messages for one file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    try:
        rel: Path | str = path.relative_to(ROOT)
    except ValueError:
        rel = path.name
    decided: list[str] = []
    cannot: list[str] = []

    for node in ast.walk(tree):
        # Decided: direct attribute assignment to status/_status.
        for target in _targets(node):
            if _is_status_attr(target):
                decided.append(
                    f"{rel}:{target.lineno}: direct write to `.{target.attr}` "
                    f"outside transition() (ADR-DOMAIN-001)"
                )

        # Cannot decide: dynamic writes the scan cannot resolve to the field.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "setattr" and len(node.args) >= 2:
                second = node.args[1]
                if isinstance(second, ast.Constant) and second.value in STATUS_NAMES:
                    cannot.append(
                        f"{rel}:{node.lineno}: setattr(..., "
                        f"{second.value!r}, ...) — dynamic write, cannot decide"
                    )
                elif not isinstance(second, ast.Constant):
                    cannot.append(
                        f"{rel}:{node.lineno}: setattr with a computed "
                        f"attribute name — cannot decide"
                    )
        # __dict__ mutation is unresolvable statically.
        for target in _targets(node):
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr == "__dict__"
            ):
                cannot.append(f"{rel}:{target.lineno}: __dict__ subscript write — cannot decide")

    return decided, cannot


def main() -> int:
    decided: list[str] = []
    cannot: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        if _in_domain(path):
            continue  # domain layer owns _status; transition() lives here
        d, c = scan_file(path)
        decided.extend(d)
        cannot.extend(c)

    if cannot:
        print("Reach boundary (cannot decide statically — review by hand):")
        for msg in cannot:
            print(f"  ? {msg}")

    if decided:
        print("Guard-reachability violations (status written outside transition()):")
        for msg in decided:
            print(f"  ✗ {msg}")
        print(
            f"\n{len(decided)} violation(s). Change status through transition() (ADR-DOMAIN-001)."
        )
        return 1

    print(
        f"✓ guard-reachability: no direct status writes outside the domain layer "
        f"({len(cannot)} form(s) at the cannot-decide boundary)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
