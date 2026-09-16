"""The re-coupling harness's frozen verifier is deterministic and can fail.

Covers the single-model scope receipt (1f916 #5417): the frozen, non-learning arm
decodes escaped literals exactly and, as a positive control, reports a mismatch
when the expected answer is wrong. A pass is therefore evidence, not a dead green.
"""

import json
from pathlib import Path

from scripts.recoupling_harness import frozen_verifier, run_frozen_arm, set_digest

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
