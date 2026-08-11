"""Stage 5D2 — Court verbs refuse properly, and the succession line is counted.

R-1: Each of the four court verbs must not mutate game state when eligible says no,
     and must return a readable refusal line (not the success line).
R-2: Tests that count the full extent of the succession line.
"""

import random

from gilded.peerage import report
from gilded.society.characters import SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.succession import succession_order
from gilded.ui.actions import ACTIONS


def _realm(seed=123, house="Vantrell"):
    rng = random.Random(seed)
    society = SocietyState(rng)
    return create_house_realm(house, society)


def _game(realm, seed=42, attention=3, court_verbs_used=0):
    """Build a minimal game wrapper."""
    class Game:
        pass
    game = Game()
    game.houses = [realm.house_name]
    game.realms = {realm.house_name: realm}
    game.ents_of = lambda h: []
    game.rng = random.Random(seed + 1)
    game.treasuries = {realm.house_name: 1000}
    game.prestige = {realm.house_name: 50}
    game.attention = {realm.house_name: attention}
    game.court_verbs_used = court_verbs_used
    game.turn = 1
    return game


def _snapshot(game, realm):
    """Capture game state for comparison after dispatch."""
    house = realm.house_name
    return {
        "attention": game.attention.get(house, 0),
        "court_verbs_used": getattr(game, "court_verbs_used", 0),
        "court_positions": {k: (v.id if v else None) for k, v in realm.court.positions.items()},
        "heir_flag": [c.id for c in realm.dynasty.all_characters.values()
                      if getattr(c, "is_heir", False)] +
                     [c.id for c in realm.characters if getattr(c, "is_heir", False)],
        "succession_ids": [c.id for c in succession_order(realm)],
    }


# ── PART 1: dismiss_seat refuses when eligible says no ────────────────────────


def test_dismiss_seat_refuses_no_attention():
    """dismiss_seat.dispatch returns refusal line and changes nothing when attention <= 0."""
    realm = _realm()
    game = _game(realm, attention=0)
    house = realm.house_name

    # Find a filled seat
    position_key = None
    for k, v in realm.court.positions.items():
        if v is not None:
            position_key = k.value.lower().replace(" ", "_")
            break
    assert position_key is not None, "Need a filled seat"

    action = {"dismiss_seat": position_key}
    ok, reason = ACTIONS["dismiss_seat"].eligible(game, house, action)
    assert not ok, "eligible should reject with no attention"

    snap = _snapshot(game, realm)
    result = ACTIONS["dismiss_seat"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert "attention" in result[0].lower() or "no attention" in result[0].lower(), \
        f"Refusal line should mention attention: {result[0]}"
    assert snap == after, "Game state should not change on refusal"


def test_dismiss_seat_refuses_court_verb_used():
    """dismiss_seat.dispatch returns refusal line and changes nothing when court verb already used."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=1)
    house = realm.house_name

    position_key = None
    for k, v in realm.court.positions.items():
        if v is not None:
            position_key = k.value.lower().replace(" ", "_")
            break
    assert position_key is not None

    action = {"dismiss_seat": position_key}
    ok, reason = ACTIONS["dismiss_seat"].eligible(game, house, action)
    assert not ok

    snap = _snapshot(game, realm)
    result = ACTIONS["dismiss_seat"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


def test_dismiss_seat_works_when_eligible():
    """dismiss_seat still dismisses when eligible says yes."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=0)
    house = realm.house_name

    position_key = None
    for k, v in realm.court.positions.items():
        if v is not None:
            position_key = k.value.lower().replace(" ", "_")
            break
    assert position_key is not None

    action = {"dismiss_seat": position_key}
    ok, reason = ACTIONS["dismiss_seat"].eligible(game, house, action)
    assert ok, f"Should be eligible: {reason}"

    snap = _snapshot(game, realm)
    result = ACTIONS["dismiss_seat"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap != after, "Game state should change on success"
    assert "dismissed" in result[0].lower(), f"Success line: {result[0]}"


# ── PART 2: appoint_to_seat refuses when eligible says no ─────────────────────


def test_appoint_to_seat_refuses_no_attention():
    """appoint_to_seat.dispatch returns refusal line and changes nothing when attention <= 0."""
    realm = _realm()
    game = _game(realm, attention=0)
    house = realm.house_name

    # Need an empty seat and a candidate — find a seat that's filled to get a key,
    # then dismiss it first to create an opening (but we can't, no attention).
    # Instead, find a position key and a candidate from dynasty.
    position_key = None
    for k in realm.court.positions:
        position_key = k.value.lower().replace(" ", "_")
        break

    # Find a candidate
    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break

    action = {"appoint_to_seat": position_key, "char_id": candidate.id}
    snap = _snapshot(game, realm)
    result = ACTIONS["appoint_to_seat"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


def test_appoint_to_seat_refuses_court_verb_used():
    """appoint_to_seat.dispatch returns refusal line and changes nothing when court verb already used."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=1)
    house = realm.house_name

    position_key = None
    for k in realm.court.positions:
        position_key = k.value.lower().replace(" ", "_")
        break

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break

    action = {"appoint_to_seat": position_key, "char_id": candidate.id}
    snap = _snapshot(game, realm)
    result = ACTIONS["appoint_to_seat"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


# ── PART 3: designate_heir refuses when eligible says no ──────────────────────


def test_designate_heir_refuses_no_attention():
    """designate_heir.dispatch returns refusal line and changes nothing when attention <= 0."""
    realm = _realm()
    game = _game(realm, attention=0)
    house = realm.house_name

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    assert candidate is not None

    action = {"char_id": candidate.id}
    ok, reason = ACTIONS["designate_heir"].eligible(game, house, action)
    assert not ok, "eligible should reject with no attention"

    snap = _snapshot(game, realm)
    result = ACTIONS["designate_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert "designated" not in result[0].lower(), \
        f"Refusal line should not be the success line: {result[0]}"
    assert snap == after, "Game state should not change on refusal"


def test_designate_heir_refuses_court_verb_used():
    """designate_heir.dispatch returns refusal line and changes nothing when court verb already used."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=1)
    house = realm.house_name

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    assert candidate is not None

    action = {"char_id": candidate.id}
    ok, reason = ACTIONS["designate_heir"].eligible(game, house, action)
    assert not ok

    snap = _snapshot(game, realm)
    result = ACTIONS["designate_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


def test_designate_heir_works_when_eligible():
    """designate_heir still designates when eligible says yes."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=0)
    house = realm.house_name

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    assert candidate is not None

    action = {"char_id": candidate.id}
    ok, reason = ACTIONS["designate_heir"].eligible(game, house, action)
    assert ok, f"Should be eligible: {reason}"

    snap = _snapshot(game, realm)
    result = ACTIONS["designate_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap != after, "Game state should change on success"
    assert "designated" in result[0].lower(), f"Success line: {result[0]}"


# ── PART 4: clear_heir refuses when eligible says no ──────────────────────────


def test_clear_heir_refuses_no_attention():
    """clear_heir.dispatch returns refusal line and changes nothing when attention <= 0."""
    realm = _realm()
    game = _game(realm, attention=0)
    house = realm.house_name

    # First designate an heir so there's something to clear
    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    candidate.is_heir = True

    action = {}
    ok, reason = ACTIONS["clear_heir"].eligible(game, house, action)
    assert not ok, "eligible should reject with no attention"

    snap = _snapshot(game, realm)
    result = ACTIONS["clear_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


def test_clear_heir_refuses_court_verb_used():
    """clear_heir.dispatch returns refusal line and changes nothing when court verb already used."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=1)
    house = realm.house_name

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    candidate.is_heir = True

    action = {}
    ok, reason = ACTIONS["clear_heir"].eligible(game, house, action)
    assert not ok

    snap = _snapshot(game, realm)
    result = ACTIONS["clear_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap == after, "Game state should not change on refusal"


def test_clear_heir_works_when_eligible():
    """clear_heir still clears when eligible says yes."""
    realm = _realm()
    game = _game(realm, attention=3, court_verbs_used=0)
    house = realm.house_name

    candidate = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != realm.ruler.id:
            candidate = c
            break
    candidate.is_heir = True

    action = {}
    ok, reason = ACTIONS["clear_heir"].eligible(game, house, action)
    assert ok, f"Should be eligible: {reason}"

    snap = _snapshot(game, realm)
    result = ACTIONS["clear_heir"].dispatch(game, house, None, action)
    after = _snapshot(game, realm)

    assert result != [], "dispatch should return a line"
    assert snap != after, "Game state should change on success"


# ── PART 5: Succession line extent tests ──────────────────────────────────────


def _living_non_ruler_ids(realm):
    """Return the set of char_ids for every living person in the realm except the ruler."""
    ruler_id = realm.ruler.id if realm.ruler else None
    ids = set()
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != ruler_id:
            ids.add(c.id)
    for c in realm.characters:
        if c.is_alive and c.id != ruler_id:
            ids.add(c.id)
    return ids


def test_succession_line_contains_all_living_non_ruler():
    """succession_order returns every living non-ruler in the realm."""
    realm = _realm()
    order = succession_order(realm)
    order_ids = [c.id for c in order]
    expected = _living_non_ruler_ids(realm)

    actual = set(order_ids)
    assert actual == expected, \
        f"Line extent mismatch: missing={expected - actual}, extra={actual - expected}"


def test_succession_line_length_equals_living_non_ruler_count():
    """The length of the line equals the count of living non-ruler realm members."""
    realm = _realm()
    order = succession_order(realm)
    expected_count = len(_living_non_ruler_ids(realm))

    assert len(order) == expected_count, \
        f"Line length {len(order)} != expected {expected_count}"


def test_succession_line_no_duplicates():
    """No character appears twice in the succession line."""
    realm = _realm()
    order = succession_order(realm)
    order_ids = [c.id for c in order]

    assert len(order_ids) == len(set(order_ids)), \
        "Line contains duplicate character IDs"


def test_succession_line_length_58_seed_123():
    """At seed 123, the succession line is 58 long (FACT 2 premise)."""
    realm = _realm(seed=123)
    order = succession_order(realm)
    assert len(order) == 58, f"Expected 58, got {len(order)}"


def test_succession_line_with_heir_still_full_extent():
    """With a designated heir, the line still contains all living non-ruler members."""
    realm = _realm()
    order = succession_order(realm)
    assert len(order) >= 2, "Need at least 2 for heir + rest"

    # Designate the second person as heir
    heir = order[1]
    heir.is_heir = True

    new_order = succession_order(realm)
    expected = _living_non_ruler_ids(realm)
    actual = set(c.id for c in new_order)

    assert actual == expected, \
        f"Line with heir: missing={expected - actual}, extra={actual - expected}"
    assert new_order[0].id == heir.id, "Designated heir should be first"

    heir.is_heir = False


def test_succession_line_no_ruler():
    """The ruler does not appear in the succession line."""
    realm = _realm()
    order = succession_order(realm)
    ruler_id = realm.ruler.id

    order_ids = [c.id for c in order]
    assert ruler_id not in order_ids, \
        f"Ruler {ruler_id} should not be in succession line"
