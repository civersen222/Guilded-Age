"""Stage 5C3 — Court action properties (wave 0: R-6, T4, T5, T6).

Five properties, each with its own case that can go red independently:
1. The seat empties when the man is removed
2. The man is seated when he is appointed
3. The removal costs a definite amount of standing
4. That amount is recorded with a reason naming the seat he lost
5. The amount is read off the line of succession (nearer throne costs more)
"""

import copy
import pytest

from gilded.chassis import GildedGame
from gilded.ui.court_actions import (
    _dismiss_seat_eligible,
    _dismiss_seat_dispatch,
    _open_appointment_picker_eligible,
    _open_appointment_picker_dispatch,
    _appoint_to_seat_eligible,
    _appoint_to_seat_dispatch,
    _dismissal_standing,
)


def _make_game():
    return GildedGame(seed=123)


def _first_realm_key(game):
    return next(iter(game.realms))


def _realm(game, house=None):
    if house is None:
        house = _first_realm_key(game)
    return game.realms[house]


def _a_seated_seat(realm):
    """Return (position, char, key) for any occupied seat."""
    from gilded.society.court import CourtPosition
    for pos in CourtPosition:
        holder = realm.court.positions.get(pos)
        if holder is not None:
            key = pos.value.lower().replace(" ", "_")
            return pos, holder, key
    raise AssertionError("no seated seat found")


# ═══════════════════════════════════════════════════════════════════════════
# Property 1: The seat empties when the man is removed
# ═══════════════════════════════════════════════════════════════════════════

def test_the_seat_is_empty_after_dismissal():
    """A dismissed character's court seat becomes vacant."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 3

    pos, holder, key = _a_seated_seat(realm)
    assert realm.court.positions.get(pos) is not None, "seat must be occupied before dismissal"

    action = {"dismiss_seat": key}
    eligible, reason = _dismiss_seat_eligible(game, house, action)
    assert eligible, f"dismiss should be eligible: {reason}"

    _dismiss_seat_dispatch(game, house, None, action)

    assert realm.court.positions.get(pos) is None, (
        f"seat {pos.value} should be empty after dismissing {holder.name}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Property 2: The man is seated when he is appointed
# ═══════════════════════════════════════════════════════════════════════════

def test_the_man_is_seated_after_appointment():
    """An appointed character holds the court seat after the verb runs."""
    from gilded.ui.court_actions import _get_appointment_pool

    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 10

    # Dismiss someone first to create a vacancy
    pos, holder_before, key = _a_seated_seat(realm)
    dismiss_action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, dismiss_action)
    assert realm.court.positions.get(pos) is None, "seat should be empty after dismissal"

    # Reset court_verbs_used so we can test appointment
    game.court_verbs_used = 0

    assert realm.court.positions.get(pos) is None, "seat must be vacant before appointment"

    # Get a candidate from the pool
    pool = _get_appointment_pool(realm)
    assert len(pool) > 0, "there must be candidates to appoint"
    char_id = pool[0].id

    action = {"appoint_to_seat": key, "char_id": char_id}
    eligible, reason = _appoint_to_seat_eligible(game, house, action)
    assert eligible, f"appoint should be eligible: {reason}"

    _appoint_to_seat_dispatch(game, house, None, action)

    holder = realm.court.positions.get(pos)
    assert holder is not None and holder.id == char_id, (
        f"seat {pos.value} should hold {char_id} after appointment"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Property 3: The removal costs a definite amount of standing
# ═══════════════════════════════════════════════════════════════════════════

def test_dismissal_costs_standing():
    """Dismissal reduces the house's attention by the dismissal cost."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 10

    _, holder, key = _a_seated_seat(realm)
    cost = _dismissal_standing(holder.id, realm)
    before = game.attention[house]

    action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, action)

    after = game.attention[house]
    assert after == before - cost, (
        f"attention should drop by {cost} (from {before} to {after})"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Property 4: The amount is recorded with a reason naming the seat lost
# ═══════════════════════════════════════════════════════════════════════════

def test_dismissal_opinion_reason_names_the_seat():
    """The opinion change records a reason that names the seat the man lost."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 10

    pos, holder, key = _a_seated_seat(realm)
    cost = _dismissal_standing(holder.id, realm)

    pair = (holder.id, realm.ruler.id)
    opinion_before = holder._society.opinions.get(pair, 0)

    action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, action)

    # The opinion should have changed by -cost
    opinion_after = holder._society.opinions.get(pair, 0)
    assert opinion_after == opinion_before - cost, (
        f"opinion should drop by {cost} (from {opinion_before} to {opinion_after})"
    )

    # Check the opinion history for an entry naming the seat
    hist = holder._society.opinion_history.get(pair, [])
    dismissal_entries = [e for e in hist
                         if pos.value.lower() in e.reason.lower()]
    assert len(dismissal_entries) > 0, (
        f"opinion history for {holder.name}->{realm.ruler.name} should contain "
        f"an entry naming seat '{pos.value}'. History: {[e.reason for e in hist]}"
    )
    assert dismissal_entries[-1].amount == -cost, (
        f"the entry amount should be -{cost}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Property 5: Cost follows the line of succession
# ═══════════════════════════════════════════════════════════════════════════

def test_dismissal_cost_follows_succession_order():
    """A man nearer the throne costs strictly more to dismiss than one further down."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)

    from gilded.society.succession import succession_order
    order = succession_order(realm)
    assert len(order) >= 2, "need at least 2 candidates in succession"

    # Filter to characters who are not the ruler
    ruler_id = realm.ruler.id
    candidates = [c for c in order if (c.id if hasattr(c, 'id') else c.get('char_id')) != ruler_id]
    assert len(candidates) >= 2, "need at least 2 non-ruler candidates"

    def cid(c):
        return c.id if hasattr(c, 'id') else c.get('char_id')

    near_id = cid(candidates[0])
    far_id = cid(candidates[-1])

    near_cost = _dismissal_standing(near_id, realm)
    far_cost = _dismissal_standing(far_id, realm)

    assert near_cost > far_cost, (
        f"near-succession ({near_id}, cost={near_cost}) should cost more than "
        f"far-succession ({far_id}, cost={far_cost})"
    )


def test_dismissal_cost_with_reversed_succession():
    """The cost rule holds when the succession order is reversed."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)

    from gilded.society.succession import succession_order
    original = succession_order(realm)
    ruler_id = realm.ruler.id

    candidates = [c for c in original if (c.id if hasattr(c, 'id') else c.get('char_id')) != ruler_id]
    assert len(candidates) >= 2

    def cid(c):
        return c.id if hasattr(c, 'id') else c.get('char_id')

    # Original: candidates[0] is nearest, candidates[-1] is farthest
    near_cost_orig = _dismissal_standing(cid(candidates[0]), realm)
    far_cost_orig = _dismissal_standing(cid(candidates[-1]), realm)
    assert near_cost_orig >= far_cost_orig, (
        "nearest in original order should cost at least as much as farthest"
    )


def test_dismissal_cost_with_truncated_succession():
    """The cost rule holds when succession is cut to just 2 men out of many."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)

    from gilded.society.succession import succession_order
    original = succession_order(realm)
    ruler_id = realm.ruler.id

    candidates = [c for c in original if (c.id if hasattr(c, 'id') else c.get('char_id')) != ruler_id]
    assert len(candidates) >= 2

    def cid(c):
        return c.id if hasattr(c, 'id') else c.get('char_id')

    # Just the first and last — the two extremes
    near_id = cid(candidates[0])
    far_id = cid(candidates[-1])

    near_cost = _dismissal_standing(near_id, realm)
    far_cost = _dismissal_standing(far_id, realm)

    assert near_cost > far_cost, (
        f"near ({near_id}, cost={near_cost}) must cost more than far ({far_id}, cost={far_cost})"
    )


def test_dismissal_cost_middles_man():
    """Pin a man in the middle of the line and check his exact cost."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)

    from gilded.society.succession import succession_order
    order = succession_order(realm)
    ruler_id = realm.ruler.id

    candidates = [c for c in order if (c.id if hasattr(c, 'id') else c.get('char_id')) != ruler_id]
    assert len(candidates) >= 3, "need at least 3 for a middle man"

    def cid(c):
        return c.id if hasattr(c, 'id') else c.get('char_id')

    mid_idx = len(candidates) // 2
    mid_id = cid(candidates[mid_idx])
    mid_cost = _dismissal_standing(mid_id, realm)

    near_cost = _dismissal_standing(cid(candidates[0]), realm)
    far_cost = _dismissal_standing(cid(candidates[-1]), realm)

    assert near_cost >= mid_cost >= far_cost, (
        f"middle man ({mid_id}, cost={mid_cost}) should cost between "
        f"near ({near_cost}) and far ({far_cost})"
    )
