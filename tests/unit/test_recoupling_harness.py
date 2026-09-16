"""The re-coupling harness's frozen verifier is deterministic and can fail.

Covers the single-model scope receipt (1f916 #5417): the frozen, non-learning arm
decodes escaped literals exactly and, as a positive control, reports a mismatch
when the expected answer is wrong. A pass is therefore evidence, not a dead green.
"""

import hashlib
import json
from pathlib import Path

from scripts.recoupling_harness import (
    copy_stamp,
    cross_copy_check,
    frozen_verifier,
    run_frozen_arm,
    set_digest,
)

FAULTSET = Path("scripts/eval_tasks/recoupling_faultset.json")


def _items() -> list[dict]:
    return json.loads(FAULTSET.read_text())["items"]


def test_frozen_verifier_decodes_every_canonical_answer() -> None:
    passed, total, failures = run_frozen_arm(_items())
    assert failures == []
    assert passed == total
    assert total >= 1


def test_frozen_verifier_can_fail_on_a_wrong_answer() -> None:
    # Positive control: corrupt one expected answer, the arm must catch it.
    items = [dict(i) for i in _items()]
    items[0]["canonical"] = "definitely-not-the-decoded-value"
    passed, total, failures = run_frozen_arm(items)
    assert items[0]["id"] in failures
    assert passed == total - 1


def test_frozen_verifier_decodes_unicode_escapes() -> None:
    # \u00fc is u-umlaut; the escaped form has no fluent idiom to normalize into.
    import hashlib

    expected = hashlib.sha256("ü".encode()).hexdigest()
    assert frozen_verifier("\\u00fc") == expected


def test_set_digest_is_stable_and_short() -> None:
    d1 = set_digest(_items())
    d2 = set_digest(_items())
    assert d1 == d2
    assert len(d1) == 16


# --- copy identity (Shadow-Alpha #5560 c64390: which copy ran, against what state) ---


def test_copy_stamp_matches_the_executing_file() -> None:
    harness = Path("scripts/recoupling_harness.py")
    expected = hashlib.sha256(harness.read_text().encode()).hexdigest()[:12]
    assert copy_stamp() == expected


def test_cross_copy_check_flags_a_divergent_copy(tmp_path: Path) -> None:
    # Positive control / zora's harness-only mutant: identical copies agree,
    # a one-byte-divergent copy produces a different hash and is caught.
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    a.write_text("VERSION = 1\n")
    b.write_text("VERSION = 1\n")
    c.write_text("VERSION = 1 \n")  # one-byte drift
    hashes = cross_copy_check([a, b, c])
    assert hashes[str(a)] == hashes[str(b)]
    assert hashes[str(c)] != hashes[str(a)]
    assert len(set(hashes.values())) == 2  # drift is visible


def test_cross_copy_check_skips_missing_paths(tmp_path: Path) -> None:
    present = tmp_path / "present.py"
    present.write_text("x = 1\n")
    missing = tmp_path / "nope.py"
    hashes = cross_copy_check([present, missing])
    assert str(present) in hashes
    assert str(missing) not in hashes
