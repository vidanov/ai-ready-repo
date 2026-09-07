#!/usr/bin/env python3
"""Generic F-004 dead-guard falsifier, decoupled from any one example.

The failure class (whitehat-explorer, 1f916 #2807 c28040): a guard placed on an
unreachable branch is present in the file but never fires on the executed path.
A textual (grep) done-condition passes on it; a behavioral one does not.

This module holds the *universal* proof procedure. It knows nothing about
discounts, orders, or any specific surface. A caller fills four slots for its
own surface and calls run(); the four steps below are the same for every
surface, which is the whole point of a portable falsifier registry entry:

  1. reference on probe_input   -> guard MUST fire (raise)
  2. dead_variant on probe_input -> guard MUST NOT fire (dead)
  3. grep guard_pattern          -> MUST match BOTH sources
  4. assert: fired AND silent AND matched_both

If a surface cannot fill these slots, F-004 does not apply to it. If it can,
this runner proves the behavioral done-condition separates the live guard from
the dead one and that grep cannot. The example-specific glue lives in the
caller (see scripts/eval_tasks/dead_guard_verify.py), not here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class DeadGuardResult:
    """The four universal observations plus the verdict.

    Named fields, never a collapsed bool: a caller (or a receipt) must be able
    to see WHICH of the three claims failed, not just that the whole thing did.
    """

    reference_fires: bool
    variant_is_dead: bool
    grep_matches_both: bool
    ok: bool


def _raises_valueerror(fn: Callable[..., Any], probe_input: dict[str, Any]) -> bool:
    """True iff calling fn(**probe_input) raises ValueError.

    ValueError is the guard signal for this class. A surface whose guard raises
    a different exception type passes its own type here by wrapping fn.
    """
    try:
        fn(**probe_input)
    except ValueError:
        return True
    return False


def run(
    reference_fn: Callable[..., Any],
    dead_variant_fn: Callable[..., Any],
    probe_input: dict[str, Any],
    guard_pattern: str,
    reference_source: str,
    variant_source: str,
) -> DeadGuardResult:
    """Run the F-004 falsifier against filled slots.

    Args mirror the registry entry's slots:
      reference_fn      -- correct implementation (guard on executed path)
      dead_variant_fn   -- same surface, guard moved to an unreachable branch
      probe_input       -- an input that MUST take the executed path
      guard_pattern     -- the textual marker a naive done-condition greps for
      reference_source  -- source text of the reference (for the grep step)
      variant_source    -- source text of the dead variant (for the grep step)
    """
    reference_fires = _raises_valueerror(reference_fn, probe_input)
    # The dead variant must NOT fire on the executed path -> variant_is_dead.
    variant_is_dead = not _raises_valueerror(dead_variant_fn, probe_input)
    grep_matches_both = guard_pattern in reference_source and guard_pattern in variant_source

    ok = reference_fires and variant_is_dead and grep_matches_both
    return DeadGuardResult(
        reference_fires=reference_fires,
        variant_is_dead=variant_is_dead,
        grep_matches_both=grep_matches_both,
        ok=ok,
    )


# ── Step 2: portable specs ───────────────────────────────────────────────────
#
# A spec fills the four slots declaratively, so another surface can port F-004
# by writing a spec instead of Python. The spec carries source strings (not live
# functions) because a falsifier registry entry has to be data, not code, to be
# shared. run_from_spec compiles the sources and calls run().
#
# TRUST BOUNDARY: run_from_spec executes the spec's source strings. That is safe
# only for specs reviewed like code (repo-local, same trust as the tests). It is
# NOT safe for specs pulled from an untrusted party -- running a stranger's spec
# is running a stranger's code. That is the custody problem (Step 3): a shared
# registry needs provenance a puller can trust before any exec. Until then,
# specs are first-party only.

REQUIRED_SPEC_KEYS = {
    "entry",  # function name defined in both sources
    "reference_source",
    "variant_source",
    "probe_input",
    "guard_pattern",
}


class SpecError(ValueError):
    """A spec is malformed -- distinct from a falsifier that ran and failed.

    A malformed spec is a measurement_invalid: the runner could not even look.
    Raising rather than returning a DeadGuardResult keeps the two disjoint.
    """


def _compile_entry(source: str, entry: str) -> Callable[..., Any]:
    ns: dict[str, Any] = {}
    exec(source, ns)  # noqa: S102 - first-party reviewed spec source only
    fn = ns.get(entry)
    if not callable(fn):
        raise SpecError(f"spec entry {entry!r} is not a callable in its source")
    return fn


def run_from_spec(spec: dict[str, Any]) -> DeadGuardResult:
    """Run the F-004 falsifier from a declarative spec.

    The spec is data: source strings, a probe input, a grep pattern, and the
    entry-point name. This is the portability layer -- a second surface writes a
    spec, not code, and gets the same run() verdict.
    """
    missing = REQUIRED_SPEC_KEYS - spec.keys()
    if missing:
        raise SpecError(f"spec missing required keys: {sorted(missing)}")
    if not isinstance(spec["probe_input"], dict):
        raise SpecError("spec probe_input must be a mapping of kwargs")

    entry = spec["entry"]
    reference_fn = _compile_entry(spec["reference_source"], entry)
    dead_variant_fn = _compile_entry(spec["variant_source"], entry)

    return run(
        reference_fn=reference_fn,
        dead_variant_fn=dead_variant_fn,
        probe_input=spec["probe_input"],
        guard_pattern=spec["guard_pattern"],
        reference_source=spec["reference_source"],
        variant_source=spec["variant_source"],
    )
