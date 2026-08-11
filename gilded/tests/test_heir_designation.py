"""Stage 5D — Heir designation tests.

New file — all cases are new since the base commit.
Tests R-1 (succession ordering), R-2 (verb), R-3 (read-model + tab),
and R-4 (chains_pack1 repair).
"""

import copy
import random

from gilded.peerage import report
from gilded.society.characters import SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.succession import succession_order, resolve_succession
from gilded.ui.actions import ACTIONS


def _realm(seed=123, house="Vantrell"):
    rng = random.Random(seed)
    society = SocietyState(rng)
    return create_house_realm(house, society)


def _game(realm, seed=42):
    """Build a minimal game wrapper for report()."""
    class Game:
        pass
    game = Game()
    game.houses = [realm.house_name]
    game.realms = {realm.house_name: realm}
    game.ents_of = lambda h: []
    game.rng = random.Random(seed + 1)
    game.treasuries = {realm.house_name: 1000}
    game.prestige = {realm.house_name: 50}
    game.attention = {realm.house_name: 3}
    game.court_verbs_used = 0
    return game


# ── R-1: Succession order honours designation ────────────────────────────────


def test_line_length_unchanged_with_designation():
    """Designation is a reordering — the line length does not change."""
    realm = _realm()
    ruler = realm.ruler
    ruler_id = ruler.id if ruler else None
    
    base_order = succession_order(realm)
    base_len = len(base_order)
    
    # Designate the LAST man in the line
    last_man = base_order[-1]
    last_man.is_heir = True
    
    new_order = succession_order(realm)
    assert len(new_order) == base_len, \
        f"Line length changed: {base_len} -> {len(new_order)}"
    
    # Clean up
    last_man.is_heir = False


def test_designated_stands_first():
    """A living designated heir stands FIRST in succession_order."""
    realm = _realm()
    ruler = realm.ruler
    ruler_id = ruler.id if ruler else None
    
    base_order = succession_order(realm)
    # Designate the LAST man
    last_man = base_order[-1]
    last_man.is_heir = True
    
    new_order = succession_order(realm)
    assert new_order[0].id == last_man.id, \
        f"Designated heir not first: {new_order[0].id} != {last_man.id}"
    
    last_man.is_heir = False


def test_designated_last_man():
    """Designate the LAST man in the 58-line and he stands first."""
    realm = _realm()
    order = succession_order(realm)
    last_id = order[-1].id
    
    # Find the character and set heir
    for c in realm.dynasty.all_characters.values():
        if c.id == last_id:
            c.is_heir = True
            break
    else:
        for c in realm.characters:
            if c.id == last_id:
                c.is_heir = True
                break
    
    new_order = succession_order(realm)
    assert new_order[0].id == last_id, \
        f"Last man not first after designation: {new_order[0].id} != {last_id}"


def test_order_behind_designated_unchanged():
    """Behind the designated man, the order is unchanged."""
    realm = _realm()
    base_order = succession_order(realm)
    base_ids = [c.id for c in base_order]
    
    # Designate the LAST man
    last_man = base_order[-1]
    last_man.is_heir = True
    
    new_order = succession_order(realm)
    new_ids = [c.id for c in new_order]
    
    # First is the designated man, rest is base order without him
    expected = [last_man.id] + [cid for cid in base_ids if cid != last_man.id]
    assert new_ids == expected, \
        f"Order behind designated man changed"
    
    last_man.is_heir = False


def test_no_designation_returns_base_order():
    """With nobody designated, the line is byte-for-byte what it was."""
    realm = _realm()
    order1 = succession_order(realm)
    order2 = succession_order(realm)
    assert [c.id for c in order1] == [c.id for c in order2], \
        "Base order is not stable"


def test_clear_designation_restores_order():
    """Clearing the designation restores the neutral line exactly."""
    realm = _realm()
    base_order = succession_order(realm)
    base_ids = [c.id for c in base_order]
    
    # Designate someone
    man = base_order[-1]
    man.is_heir = True
    
    # Clear designation
    man.is_heir = False
    
    new_order = succession_order(realm)
    new_ids = [c.id for c in new_order]
    assert new_ids == base_ids, \
        "Clearing designation did not restore base order"


# ── R-1: resolve_succession returns designated heir ──────────────────────────


def test_resolve_returns_designated():
    """resolve_succession returns the designated man."""
    realm = _realm()
    order = succession_order(realm)
    last_man = order[-1]
    last_man.is_heir = True
    
    heir = resolve_succession(realm)
    assert heir is not None and heir.id == last_man.id, \
        f"resolve_succession did not return designated heir"
    
    last_man.is_heir = False


def test_resolve_returns_none_without_designation():
    """Without designation, resolve returns whoever stands first (unchanged)."""
    realm = _realm()
    heir = resolve_succession(realm)
    assert heir is not None, "resolve_succession returned None"
    # Should be the first in the base order
    order = succession_order(realm)
    assert heir.id == order[0].id


# ── R-3: Read-model names designated heir ────────────────────────────────────


def test_read_model_names_designated():
    """CourtReport.heir_designated is the name of the designated heir."""
    realm = _realm()
    game = _game(realm)
    
    # Designate someone
    order = succession_order(realm)
    man = order[-1]
    man.is_heir = True
    
    r = report(game, realm.house_name)
    assert r.heir_designated == man.name, \
        f"Read-model heir_designated wrong: {r.heir_designated} != {man.name}"
    
    man.is_heir = False


def test_read_model_says_none_without_designation():
    """CourtReport.heir_designated is None when nobody is designated."""
    realm = _realm()
    game = _game(realm)
    
    r = report(game, realm.house_name)
    assert r.heir_designated is None, \
        f"Read-model should be None: {r.heir_designated}"


def test_read_model_different_men_different_names():
    """Naming man A vs man B produces different heir_designated values."""
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    man_a = order[-1]
    man_b = order[-2]
    
    man_a.is_heir = True
    r_a = report(game, realm.house_name)
    
    man_a.is_heir = False
    man_b.is_heir = True
    r_b = report(game, realm.house_name)
    
    assert r_a.heir_designated != r_b.heir_designated, \
        f"Different men should produce different heir_designated"
    
    man_b.is_heir = False


# ── R-4: Chains pack triggers fixed ──────────────────────────────────────────


def test_heir_chain_arms_with_premise():
    """heir_radicalization trigger arms when is_heir is set and labor_capital <= -30."""
    from gilded.society.event_content.chains_pack1 import _trig_heir_radicalization
    
    realm = _realm()
    game = _game(realm)
    
    # Find a character and set up the premise
    order = succession_order(realm)
    heir = order[-1]
    heir.is_heir = True
    heir.dispositions["labor_capital"] = -40.0
    
    ctx = _trig_heir_radicalization(game)
    assert ctx is not None, "heir_radicalization trigger did not arm"
    assert ctx["heir"] == heir.name, \
        f"Context heir wrong: {ctx['heir']} != {heir.name}"
    
    heir.is_heir = False


def test_heir_chain_context_house_is_realms_key():
    """heir_radicalization context house value is a key of game.realms."""
    from gilded.society.event_content.chains_pack1 import _trig_heir_radicalization
    
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    heir = order[-1]
    heir.is_heir = True
    heir.dispositions["labor_capital"] = -40.0
    
    ctx = _trig_heir_radicalization(game)
    assert ctx["house"] in game.realms, \
        f"Context house '{ctx['house']}' not in game.realms keys"
    
    heir.is_heir = False


def test_chain_beats_cost_heir_and_house():
    """heir chain beats cost the heir labor_capital/stress and house legitimacy."""
    from gilded.society.event_content.chains_pack1 import (
        _heir_pamphlet, _heir_refusal, _trig_heir_radicalization,
    )
    
    realm = _realm()
    game = _game(realm)
    game.legitimacy = {realm.house_name: 50.0}
    
    order = succession_order(realm)
    heir = order[-1]
    heir.is_heir = True
    heir.dispositions["labor_capital"] = -40.0
    
    ctx = _trig_heir_radicalization(game)
    initial_lc = heir.dispositions["labor_capital"]
    initial_stress = getattr(heir, "stress", 0.0)
    initial_legit = game.legitimacy[realm.house_name]
    
    # Apply pamphlet beat
    _heir_pamphlet(game, ctx)
    assert heir.dispositions["labor_capital"] < initial_lc, \
        "Pamphlet did not reduce labor_capital"
    assert game.legitimacy[realm.house_name] < initial_legit, \
        "Pamphlet did not reduce legitimacy"
    
    # Apply refusal beat
    _heir_refusal(game, ctx)
    final_stress = getattr(heir, "stress", 0.0)
    assert final_stress > initial_stress, \
        "Refusal did not increase stress"
    
    heir.is_heir = False


# ── R-2: Verb in ACTIONS ────────────────────────────────────────────────────


def test_designate_heir_in_actions():
    """designate_heir is a key in ACTIONS."""
    assert "designate_heir" in ACTIONS, \
        "designate_heir not registered in ACTIONS"


def test_clear_heir_in_actions():
    """clear_heir is a key in ACTIONS."""
    assert "clear_heir" in ACTIONS, \
        "clear_heir not registered in ACTIONS"


# ── R-2: Verb refuses invalid targets ────────────────────────────────────────


def test_verb_refuses_dead_man():
    """Verb refuses a dead man."""
    from gilded.ui.court_actions import _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    dead_man = order[-1]
    dead_man.is_alive = False
    
    action = {"char_id": dead_man.id}
    ok, reason = _designate_heir_eligible(game, realm.house_name, action)
    assert not ok, "Verb should refuse dead man"
    assert reason, "Refusal should have a reason"
    
    dead_man.is_alive = True


def test_verb_refuses_ruler():
    """Verb refuses the ruler."""
    from gilded.ui.court_actions import _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    
    action = {"char_id": realm.ruler.id}
    ok, reason = _designate_heir_eligible(game, realm.house_name, action)
    assert not ok, "Verb should refuse ruler"
    assert reason, "Refusal should have a reason"


def test_verb_refuses_no_attention():
    """Verb refused when house has no attention."""
    from gilded.ui.court_actions import _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    game.attention[realm.house_name] = 0
    
    order = succession_order(realm)
    man = order[-1]
    action = {"char_id": man.id}
    ok, reason = _designate_heir_eligible(game, realm.house_name, action)
    assert not ok, "Verb should refuse with no attention"
    assert reason, "Refusal should have a reason"


def test_verb_refuses_action_spent():
    """Verb refused when court action already spent."""
    from gilded.ui.court_actions import _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    game.court_verbs_used = 1
    
    order = succession_order(realm)
    man = order[-1]
    action = {"char_id": man.id}
    ok, reason = _designate_heir_eligible(game, realm.house_name, action)
    assert not ok, "Verb should refuse when action spent"
    assert reason, "Refusal should have a reason"


# ── R-2: Verb dispatch designates and costs attention ────────────────────────


def test_dispatch_designates_man():
    """Dispatch leaves the man designated and first in line."""
    from gilded.ui.court_actions import _designate_heir_dispatch, _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    man = order[-1]
    action = {"char_id": man.id}
    
    ok, _ = _designate_heir_eligible(game, realm.house_name, action)
    assert ok, "Should be eligible"
    
    _designate_heir_dispatch(game, realm.house_name, None, action)
    
    # Check designation
    assert man.is_heir, "Man not designated after dispatch"
    
    # Check succession order
    new_order = succession_order(realm)
    assert new_order[0].id == man.id, \
        "Designated man not first in succession"
    
    # Check attention cost
    assert game.attention[realm.house_name] == 2, \
        f"Attention not reduced: {game.attention[realm.house_name]}"


def test_naming_second_man_replaces_first():
    """Naming a second man leaves exactly one designated heir."""
    from gilded.ui.court_actions import _designate_heir_dispatch, _designate_heir_eligible
    
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    man_a = order[-1]
    man_b = order[-2]
    
    # Designate man A
    action_a = {"char_id": man_a.id}
    _designate_heir_dispatch(game, realm.house_name, None, action_a)
    assert man_a.is_heir
    
    game.attention[realm.house_name] = 3
    game.court_verbs_used = 0
    
    # Designate man B
    action_b = {"char_id": man_b.id}
    ok, _ = _designate_heir_eligible(game, realm.house_name, action_b)
    assert ok, "Should be eligible"
    _designate_heir_dispatch(game, realm.house_name, None, action_b)
    
    assert man_b.is_heir, "Second man not designated"
    assert not man_a.is_heir, "First man still designated"


# ── R-3: House tab shows designation ─────────────────────────────────────────


def test_house_tab_shows_designation():
    """House tab drawn with a designated heir differs from without."""
    import pygame
    from gilded.peerage import report
    from gilded.ui.house_tab import _house_tab_lines
    
    realm = _realm()
    game = _game(realm)
    
    r_without = report(game, realm.house_name)
    lines_without = _house_tab_lines(r_without)
    
    # Designate someone
    order = succession_order(realm)
    man = order[-1]
    man.is_heir = True
    
    r_with = report(game, realm.house_name)
    lines_with = _house_tab_lines(r_with)
    
    assert lines_with != lines_without, \
        "Tab lines should differ with designation"
    assert any("Designated Heir:" in line for line in lines_with), \
        "Tab should contain 'Designated Heir:' line"
    
    man.is_heir = False


def test_house_tab_different_heir_different_lines():
    """House tab with man A differs from man B."""
    from gilded.peerage import report
    from gilded.ui.house_tab import _house_tab_lines
    
    realm = _realm()
    game = _game(realm)
    
    order = succession_order(realm)
    man_a = order[-1]
    man_b = order[-2]
    
    man_a.is_heir = True
    r_a = report(game, realm.house_name)
    lines_a = _house_tab_lines(r_a)
    
    man_a.is_heir = False
    man_b.is_heir = True
    r_b = report(game, realm.house_name)
    lines_b = _house_tab_lines(r_b)
    
    assert lines_a != lines_b, \
        "Tab lines should differ for different heirs"
    
    man_b.is_heir = False
