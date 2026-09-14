"""The guard-reachability check convicts direct status writes and declares its edge.

Covers ADR-DOMAIN-001 reachability (backlog #041): status is written only through
transition(). Correctness is drilled separately (drill_transition_guard).
"""

from pathlib import Path

from scripts.check_reachability import scan_file


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
