"""The guard-reachability check convicts direct status writes and declares its edge.

Covers ADR-DOMAIN-001 reachability (backlog #041): status is written only through
transition(). Correctness is drilled separately (drill_transition_guard).
"""

from pathlib import Path

from scripts.check_reachability import scan_file
from scripts.drill_reachability_coupling import (
    _fields_written_by_transition,
    _status_names_watched_by_check,
)


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(body)
    return path


def test_direct_status_assignment_is_a_decided_violation(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "order.status = 'delivered'\n"))
    assert len(decided) == 1
    assert ".status" in decided[0]
    assert cannot == []


def test_private_status_assignment_is_a_decided_violation(tmp_path: Path) -> None:
    decided, _ = scan_file(write(tmp_path, "order._status = new\n"))
    assert len(decided) == 1
    assert "._status" in decided[0]


def test_augmented_and_annotated_assignment_are_caught(tmp_path: Path) -> None:
    decided, _ = scan_file(write(tmp_path, "o.status += 1\no._status: int = 2\n"))
    assert len(decided) == 2


def test_comparison_is_not_a_violation(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "if order.status == 'pending':\n    pass\n"))
    assert decided == []
    assert cannot == []


def test_transition_call_is_not_a_violation(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "order.transition(OrderStatus.SHIPPED)\n"))
    assert decided == []
    assert cannot == []


def test_setattr_status_is_reported_at_the_boundary_not_decided(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "setattr(order, 'status', 'delivered')\n"))
    assert decided == []
    assert len(cannot) == 1
    assert "setattr" in cannot[0]


def test_dunder_dict_write_is_reported_at_the_boundary(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "order.__dict__['status'] = 'delivered'\n"))
    assert decided == []
    assert len(cannot) == 1
    assert "__dict__" in cannot[0]


def test_unrelated_attribute_assignment_is_ignored(tmp_path: Path) -> None:
    decided, cannot = scan_file(write(tmp_path, "order.customer_id = 'c1'\n"))
    assert decided == []
    assert cannot == []


# --- coupling drill (drill_reachability_coupling, 1f916 #5465 dead-from-birth) ---


def test_coupling_discovers_field_transition_writes() -> None:
    src = "class Order:\n    def transition(self, s):\n        self._status = s\n"
    assert _fields_written_by_transition(src) == {"_status"}


def test_coupling_ignores_writes_outside_transition() -> None:
    src = (
        "class Order:\n"
        "    def other(self):\n"
        "        self._audit = 1\n"
        "    def transition(self, s):\n"
        "        self._status = s\n"
    )
    assert _fields_written_by_transition(src) == {"_status"}


def test_coupling_reads_status_names_from_check() -> None:
    src = 'STATUS_NAMES = {"status", "_status"}\n'
    assert _status_names_watched_by_check(src) == {"status", "_status"}


def test_coupling_is_detectably_broken_when_check_watches_wrong_name() -> None:
    # Positive control: a check whose watched set misses the field transition()
    # writes is decoupled, and guarded - watched is non-empty. This is the
    # condition the drill fails on.
    guarded = _fields_written_by_transition(
        "class Order:\n    def transition(self, s):\n        self._status = s\n"
    )
    watched = _status_names_watched_by_check('STATUS_NAMES = {"status", "_legacy_status"}\n')
    assert guarded - watched == {"_status"}
