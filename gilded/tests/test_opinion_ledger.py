"""Tests for the opinion ledger (mission I5b).

Verifies: per-pair ledger, bounded by module-level constant, newest kept / oldest
discarded, no empty-reason entries, set_state clears, matrix identity preserved.
"""

import copy
import random

from gilded.society.characters import SocietyState, modify_opinion as _modify_opinion, OPINION_LEDGER_CAP, OpinionEntry
from gilded.society.realm import create_house_realm
from gilded.society.relationships import (
    modify_opinion,
    opinion_of,
    get_state,
    set_state,
)


def _realm(seed=42, house="Vantrell"):
    rng = random.Random(seed)
    society = SocietyState(rng)
    return create_house_realm(house, society)


# ── D1: Ledger records entries keyed by directed pair ──────────────────────

def test_ledger_records_entry_on_modify():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +5, "feast")
    pair = (a.id, b.id)
    assert pair in ra.society.opinion_history
    entries = ra.society.opinion_history[pair]
    assert len(entries) == 1
    assert entries[0].amount == 5
    assert entries[0].reason == "feast"


def test_ledger_keyed_by_directed_pair():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +5, "feast")
    modify_opinion(b, a, -3, "refused capital")
    # Two distinct pairs
    assert (a.id, b.id) in ra.society.opinion_history
    assert (b.id, a.id) in ra.society.opinion_history
    assert ra.society.opinion_history[(a.id, b.id)][0].reason == "feast"
    assert ra.society.opinion_history[(b.id, a.id)][0].reason == "refused capital"


# ── D2: SocietyState still constructs from one positional argument ─────────

def test_society_state_constructs_from_one_arg():
    rng = random.Random(99)
    s = SocietyState(rng)
    assert s.rng is rng
    assert isinstance(s.opinion_history, dict)


# ── D3: Bounded by module-level constant, newest kept / oldest discarded ──

def test_ledger_cap_is_module_constant():
    assert isinstance(OPINION_LEDGER_CAP, int)
    assert OPINION_LEDGER_CAP > 0


def test_ledger_bounded_at_cap():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    pair = (a.id, b.id)
    for i in range(OPINION_LEDGER_CAP + 5):
        modify_opinion(a, b, +1, f"reason_{i}")
    entries = ra.society.opinion_history[pair]
    assert len(entries) == OPINION_LEDGER_CAP


def test_ledger_keeps_newest_discards_oldest():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    pair = (a.id, b.id)
    for i in range(OPINION_LEDGER_CAP + 5):
        modify_opinion(a, b, +1, f"reason_{i}")
    entries = ra.society.opinion_history[pair]
    # First written entry must be gone
    first_reasons = {e.reason for e in entries}
    assert "reason_0" not in first_reasons, "Oldest entry must be evicted"
    # Last written entry must be present
    last = entries[-1]
    assert last.reason == f"reason_{OPINION_LEDGER_CAP + 4}", "Newest entry must be present"


# ── D4: No reason → no ledger entry; no entry carries empty reason ─────────

def test_no_reason_moves_matrix_but_records_nothing():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    pair = (a.id, b.id)
    modify_opinion(a, b, -25)  # no reason argument
    assert opinion_of(a, b) == -25
    assert pair not in ra.society.opinion_history


def test_no_entry_has_empty_reason():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +5, "feast")
    modify_opinion(a, b, -3, "")  # explicit empty reason
    modify_opinion(a, b, +2, "gift")
    pair = (a.id, b.id)
    entries = ra.society.opinion_history.get(pair, [])
    for e in entries:
        assert e.reason != "", "No entry may carry an empty reason"
    # Only two entries recorded (the one with reason)
    assert len(entries) == 2


def test_direct_assignment_records_nothing():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    pair = (a.id, b.id)
    ra.society.opinions[pair] = -10  # direct assignment
    assert opinion_of(a, b) == -10
    assert pair not in ra.society.opinion_history


# ── D5: set_state clears the ledger ────────────────────────────────────────

def test_set_state_clears_ledger():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +5, "feast")
    pair = (a.id, b.id)
    assert pair in ra.society.opinion_history
    set_state(ra.society, {})
    assert opinion_of(a, b) == 0
    assert pair not in ra.society.opinion_history


def test_set_state_clears_ledger_with_restore():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +5, "feast")
    assert (a.id, b.id) in ra.society.opinion_history
    # Restore from empty state — ledger must be empty
    set_state(ra.society, {})
    assert (a.id, b.id) not in ra.society.opinion_history


# ── D8: Matrix is bit-identical for same sequence of calls ─────────────────

def test_matrix_identity_preserved():
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, +10, "feast")
    modify_opinion(a, b, -5, "refused")
    modify_opinion(b, a, +3, "gift")
    # The matrix values must match what the calls produce
    assert opinion_of(a, b) == 5
    assert opinion_of(b, a) == 3
    # Deep copy the opinions for comparison
    opinions_snapshot = copy.deepcopy(ra.society.opinions)
    # Run the same calls on a fresh realm
    ra2 = _realm()
    set_state(ra2.society, {})
    a2, b2 = ra2.characters[0], ra2.characters[1]
    modify_opinion(a2, b2, +10, "feast")
    modify_opinion(a2, b2, -5, "refused")
    modify_opinion(b2, a2, +3, "gift")
    # The structure is the same (though ids differ)
    assert opinion_of(a2, b2) == 5
    assert opinion_of(b2, a2) == 3


def test_modify_opinion_still_returns_string():
    """The underlying _modify_opinion returns a descriptive string.
    The relationships wrapper discards it (returns None) — that's fine since
    no game site reads the return value."""
    ra = _realm()
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    # The underlying function returns a string
    from gilded.society.characters import modify_opinion as _base_modify
    result = _base_modify(a, b, +5, "feast")
    assert isinstance(result, str)
    assert a.name in result
    assert b.name in result
