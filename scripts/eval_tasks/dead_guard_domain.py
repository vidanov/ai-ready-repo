"""Domain for the F-004 dead-guard eval task.

The task: ``apply_discount`` must reject a negative discount on the EXECUTED
path. The failure class being fixtured (proposed by whitehat-explorer on
1f916, post #2807, comment c28040):

  * A *present, dead* guard. A naive agent inserts the validation inside a
    branch that never fires for the tested input (here: the ``price <= 0``
    early-return branch). A textual done-condition that greps for
    "raise ValueError" (or "discount") still reads as satisfied, because the
    string is in the file. The guard never runs.

This module is the CORRECT reference implementation: the validation sits on
the executed path, before any conditional return. The verifying script
(``dead_guard_verify.py``) also constructs a dead-guard variant and proves
that a grep done-condition passes on it while the behavioral done-condition
fails -- which is exactly why textual done-conditions are not sufficient.
"""

from __future__ import annotations


def apply_discount(price: float, discount: float) -> float:
    """Apply a fractional discount; reject a negative discount.

    A negative ``discount`` (which would *increase* the price) must raise
    ``ValueError`` on the executed path, regardless of ``price``.
    """
    if discount < 0:
        raise ValueError("discount cannot be negative")
    if price <= 0:
        return price
    return price * (1 - discount)
