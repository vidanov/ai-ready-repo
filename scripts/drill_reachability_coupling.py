"""Drill: prove the reachability check is coupled to its subject, not to a string.

`drill_reachability.py` proves the check *fires* on a planted violation. That is
necessary but not sufficient: a check can fire correctly on planted faults and
still be dead from birth if its firing is not coupled to the subject it guards
(kilmon-ai's third state, 1f916 #5465; the subject-delete counterfactual replied
at c62943; peppercorn's specimen where a control and its subject "shared a string
and the string was the thing being matched", #5417 c62579).

check_reachability.py watches the field names in `STATUS_NAMES`. Its subject is
the private status field of the domain `Order`. If the domain renames that field
and `STATUS_NAMES` is left stale, the check scans for a name that no longer
carries the invariant and passes green over every write to the new one — firing
untestably on planted old-name faults while blind to real new-name ones. That is
decoupling, and no amount of planting old-name violations reveals it.

This drill runs the counterfactual: it discovers, from the domain source itself,
the field name that `transition()` actually assigns, and asserts the check is
watching exactly that name. Field renamed but check not updated => the check is
no longer about its subject, and this drill fails. It reads sources only; it
plants nothing and needs no sandbox.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAIN = ROOT / "src" / "ai_ready_repo" / "domain" / "__init__.py"
CHECK = ROOT / "scripts" / "check_reachability.py"


def _fields_written_by_transition(domain_src: str) -> set[str]:
    """The attribute names `transition()` assigns on self — the guarded field(s)."""
    tree = ast.parse(domain_src)
    written: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "transition":
            for inner in ast.walk(node):
                targets: list[ast.expr] = []
                if isinstance(inner, ast.Assign):
                    targets = list(inner.targets)
                elif isinstance(inner, ast.AugAssign | ast.AnnAssign):
                    targets = [inner.target]
                for t in targets:
                    if (
                        isinstance(t, ast.Attribute)
                        and isinstance(t.value, ast.Name)
                        and t.value.id == "self"
                    ):
                        written.add(t.attr)
    return written


def _status_names_watched_by_check(check_src: str) -> set[str]:
    """The literal set assigned to STATUS_NAMES in the check."""
    tree = ast.parse(check_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "STATUS_NAMES":
                    if isinstance(node.value, ast.Set | ast.List | ast.Tuple):
                        return {
                            e.value
                            for e in node.value.elts
                            if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        }
    return set()


def main() -> int:
    guarded = _fields_written_by_transition(DOMAIN.read_text())
    watched = _status_names_watched_by_check(CHECK.read_text())

    if not guarded:
        raise RuntimeError(
            "Could not find the field transition() assigns in the domain — "
            "the drill cannot establish coupling. Has transition() moved or been renamed?"
        )
    if not watched:
        raise RuntimeError("Could not read STATUS_NAMES from check_reachability.py.")

    # The check must watch every field transition() actually writes. If the domain
    # renamed the field and the check was not updated, `guarded - watched` is non-empty
    # and the check would pass green over writes to the new name.
    unwatched = guarded - watched
    if unwatched:
        raise RuntimeError(
            f"guard-reachability check is decoupled from its subject: transition() "
            f"writes {sorted(guarded)} but the check watches {sorted(watched)}. "
            f"Unwatched: {sorted(unwatched)}. The check would pass green over direct "
            f"writes to the renamed field (kilmon-ai's dead-from-birth, #5465)."
        )

    print(
        f"✓ drill-reachability-coupling passed: check watches {sorted(watched)}, "
        f"transition() writes {sorted(guarded)} — coupled to its subject."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
