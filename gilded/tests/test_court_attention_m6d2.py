"""Stage 5C3 — Court attention & one-verb-per-turn (wave 2: R-2, R-3).

Both court verbs refuse for want of attention and neither takes any
when attention is exhausted. Removing a man and seating a man must each
leave the house with strictly less attention. A turn that affords one
court verb must afford exactly one.
"""

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
    _get_appointment_pool,
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
# Dismissal refuses for want of attention
# ═══════════════════════════════════════════════════════════════════════════

def test_dismissal_refused_when_no_attention():
    """Dismissal is refused when the house has zero attention."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 0

    _, _, key = _a_seated_seat(realm)
    action = {"dismiss_seat": key}
    eligible, reason = _dismiss_seat_eligible(game, house, action)

    assert not eligible, "dismissal should be refused with zero attention"
    assert "attention" in reason.lower(), (
        f"refusal reason should mention attention: '{reason}'"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Appointment picker refuses for want of attention
# ═══════════════════════════════════════════════════════════════════════════

def test_appointment_picker_refused_when_no_attention():
    """Opening the appointment picker is refused when the house has zero attention."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 0

    _, _, key = _a_seated_seat(realm)
    # Dismiss to create vacancy
    dismiss_action = {"dismiss_seat": key}
    game.attention[house] = 5
    _dismiss_seat_dispatch(game, house, None, dismiss_action)
    game.attention[house] = 0

    action = {"open_appointment_picker": key}
    eligible, reason = _open_appointment_picker_eligible(game, house, action)

    assert not eligible, "picker should be refused with zero attention"
    assert "attention" in reason.lower(), (
        f"refusal reason should mention attention: '{reason}'"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Dismissal costs attention
# ═══════════════════════════════════════════════════════════════════════════

def test_dismissal_reduces_attention():
    """Dismissal leaves the house with strictly less attention than before."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 10

    _, holder, key = _a_seated_seat(realm)
    before = game.attention[house]

    action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, action)

    after = game.attention[house]
    assert after < before, (
        f"attention should be strictly less after dismissal ({before} -> {after})"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Appointment costs attention
# ═══════════════════════════════════════════════════════════════════════════

def test_appointment_reduces_attention():
    """Appointment leaves the house with strictly less attention than before."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 10

    # Dismiss someone first to create a vacancy
    pos, holder_before, key = _a_seated_seat(realm)
    dismiss_action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, dismiss_action)

    # Reset court_verbs_used
    game.court_verbs_used = 0

    before = game.attention[house]

    pool = _get_appointment_pool(realm)
    assert len(pool) > 0
    char_id = pool[0].id

    action = {"appoint_to_seat": key, "char_id": char_id}
    _appoint_to_seat_dispatch(game, house, None, action)

    after = game.attention[house]
    assert after < before, (
        f"attention should be strictly less after appointment ({before} -> {after})"
    )


# ═══════════════════════════════════════════════════════════════════════════
# One verb per turn
# ═══════════════════════════════════════════════════════════════════════════

def test_second_dismissal_refused_after_first():
    """After one dismissal, no further court verb may succeed."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 20

    _, _, key = _a_seated_seat(realm)
    action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, action)

    # Try another dismissal
    _, _, key2 = _a_seated_seat(realm)
    action2 = {"dismiss_seat": key2}
    eligible, reason = _dismiss_seat_eligible(game, house, action2)

    assert not eligible, "second dismissal should be refused"
    assert "court" in reason.lower() or "already" in reason.lower(), (
        f"refusal reason should name the limit: '{reason}'"
    )


def test_appointment_refused_after_dismissal():
    """After a dismissal, appointment is also refused (one verb per turn)."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 20

    # Dismiss someone
    pos, _, key = _a_seated_seat(realm)
    action = {"dismiss_seat": key}
    _dismiss_seat_dispatch(game, house, None, action)

    # The seat is now vacant — try to appoint
    pool = _get_appointment_pool(realm)
    assert len(pool) > 0
    char_id = pool[0].id

    action2 = {"appoint_to_seat": key, "char_id": char_id}
    eligible, reason = _appoint_to_seat_eligible(game, house, action2)

    assert not eligible, "appointment after dismissal should be refused"
    assert "court" in reason.lower() or "already" in reason.lower(), (
        f"refusal reason should name the limit: '{reason}'"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Court state unchanged after second verb refused
# ═══════════════════════════════════════════════════════════════════════════

def test_court_unchanged_after_refused_second_verb():
    """After the first verb, a refused second verb leaves the court as-is."""
    game = _make_game()
    house = _first_realm_key(game)
    realm = _realm(game, house)
    game.attention[house] = 20

    # First dismissal
    pos1, _, key1 = _a_seated_seat(realm)
    action = {"dismiss_seat": key1}
    _dismiss_seat_dispatch(game, house, None, action)

    # Record court state after first verb
    import copy
    state_after_first = {
        pos: (holder.id if holder else None)
        for pos, holder in realm.court.positions.items()
    }

    # Try second dismissal — should be refused
    pos2, _, key2 = _a_seated_seat(realm)
    action2 = {"dismiss_seat": key2}
    eligible, _ = _dismiss_seat_eligible(game, house, action2)
    assert not eligible, "second dismissal should be refused"

    # Even if we tried to dispatch, it should not change the court
    _dismiss_seat_dispatch(game, house, None, action2)

    state_after_refusal = {
        pos: (holder.id if holder else None)
        for pos, holder in realm.court.positions.items()
    }

    assert state_after_first == state_after_refusal, (
        "court state should not change after a refused second verb"
    )
