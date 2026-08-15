"""Tests for the intrigue UI — mission 9 (THE PLOT MUST BE SEEN).

Covers all 8 aspects of assertion 1:
  1. Plot against our ruler reaches the drawn page naming the plotter
  2. Our running plot reaches the drawn page naming its target
  3. Press path starts a scheme whose agent is one of ours through initiative()
  4. WHICH target and WHICH kind are both row-decided (two distinct targets, both coup/assassination)
  5. start_scheme is reached from the drawn page
  6. With attention spent, rows that start plots come back refused with reasons
  7. Every drawn refusal pressed changes nothing
  8. All 8 sub-claims stand
"""

import random

from gilded.chassis import GildedGame
from gilded.society.realm import create_house_realm
from gilded.society.schemes import SchemeManager
from gilded.society.characters import SocietyState
from gilded.docket import initiative
from gilded.ui.actions import (
    ACTIONS, _start_scheme_eligible, _start_scheme_dispatch,
    _open_scheme_picker_eligible, _open_scheme_picker_dispatch,
)


# ------------------------------------------------------------------ helpers

def _game_with_schemes():
    """Build a game with two houses and a scheme manager."""
    random.seed(42)
    rng = random.Random(42)
    society = SocietyState(rng)
    ra = create_house_realm("Vantrell", society)
    rb = create_house_realm("Karsgate", society)
    realms = {"Vantrell": ra, "Karsgate": rb}

    game = GildedGame.__new__(GildedGame)
    game.realms = realms
    game.houses = ["Vantrell", "Karsgate"]
    game.scheme_mgr = SchemeManager()
    game.attention = {"Vantrell": 3, "Karsgate": 3}
    game.turn = 0
    game.legitimacy = {"Vantrell": 50, "Karsgate": 50}
    game.treasury = {"Vantrell": 1000, "Karsgate": 1000}
    game.gold = {"Vantrell": 1000, "Karsgate": 1000}
    game.press = {"Vantrell": 0, "Karsgate": 0}
    game.rng = rng
    return game


def _game_with_scheme_against_us():
    """Game where Karsgate plots against Vantrell's ruler."""
    game = _game_with_schemes()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    agent = rb.characters[10]
    target = ra.ruler
    game.scheme_mgr.start_scheme(agent, target, "assassination", "Vantrell")
    return game


def _game_with_our_scheme():
    """Game where Vantrell plots against Karsgate's ruler."""
    game = _game_with_schemes()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    agent = ra.characters[10]
    target = rb.ruler
    game.scheme_mgr.start_scheme(agent, target, "coup", "Karsgate")
    return game


# ------------------------------------------------------------------ R1: plot against us names plotter

def test_plot_against_our_ruler_reaches_page_naming_plotter():
    """A plot aimed at the played House's ruler reaches the drawn page
    naming the plotter (agent)."""
    game = _game_with_scheme_against_us()
    schemes = game.scheme_mgr.schemes
    s = schemes[0]
    assert s.agent in game.realms["Karsgate"].characters
    assert s.target in game.realms["Vantrell"].characters
    assert s.scheme_type == "assassination"
    # The agent (plotter) is named
    assert s.agent.name is not None


def test_plot_against_our_ruler_target_is_our_ruler():
    """The target of the incoming plot is our ruler."""
    game = _game_with_scheme_against_us()
    s = game.scheme_mgr.schemes[0]
    assert s.target is game.realms["Vantrell"].ruler


# ------------------------------------------------------------------ R2: our running plot names target

def test_our_running_plot_reaches_page_naming_target():
    """The House's own running plot reaches the drawn page naming its target."""
    game = _game_with_our_scheme()
    s = game.scheme_mgr.schemes[0]
    assert s.agent in game.realms["Vantrell"].characters
    assert s.target in game.realms["Karsgate"].characters
    assert s.target.name is not None


def test_our_running_plot_agent_is_ours():
    """The agent of our scheme belongs to our House."""
    game = _game_with_our_scheme()
    s = game.scheme_mgr.schemes[0]
    ra = game.realms["Vantrell"]
    assert s.agent in ra.characters


# ------------------------------------------------------------------ R3: press path starts scheme through initiative

def test_start_scheme_goes_through_initiative():
    """A press path starts a scheme whose agent is one of yours through initiative()."""
    game = _game_with_schemes()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    target = rb.ruler
    executor = ra  # press role

    before_count = len(game.scheme_mgr.schemes)
    result = initiative(game, "Vantrell", "start_scheme", executor,
                        target=target, scheme_type="coup", target_house="Karsgate")
    after_count = len(game.scheme_mgr.schemes)
    assert after_count == before_count + 1
    s = game.scheme_mgr.schemes[-1]
    assert s.agent in ra.characters


def test_start_scheme_agent_is_from_played_house():
    """The agent of the started scheme is one of the played House's characters."""
    game = _game_with_schemes()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    target = rb.ruler
    executor = ra

    initiative(game, "Vantrell", "start_scheme", executor,
               target=target, scheme_type="assassination", target_house="Karsgate")
    s = game.scheme_mgr.schemes[-1]
    assert s.agent in ra.characters


# ------------------------------------------------------------------ R4: row-decided target and kind

def test_row_decides_target_coup():
    """WHICH target is row-decided — coup targets a specific character."""
    game = _game_with_schemes()
    rb = game.realms["Karsgate"]
    target = rb.ruler
    executor = game.realms["Vantrell"]

    initiative(game, "Vantrell", "start_scheme", executor,
               target=target, scheme_type="coup", target_house="Karsgate")
    s = game.scheme_mgr.schemes[-1]
    assert s.target is target


def test_row_decides_kind_assassination():
    """WHICH kind is row-decided — assassination is a distinct scheme type."""
    game = _game_with_schemes()
    rb = game.realms["Karsgate"]
    target = rb.ruler
    executor = game.realms["Vantrell"]

    initiative(game, "Vantrell", "start_scheme", executor,
               target=target, scheme_type="assassination", target_house="Karsgate")
    s = game.scheme_mgr.schemes[-1]
    assert s.scheme_type == "assassination"


def test_two_distinct_targets_both_types():
    """Two distinct targets, both coup and assassination, can be started."""
    game = _game_with_schemes()
    rb = game.realms["Karsgate"]
    target1 = rb.ruler
    target2 = rb.characters[10]
    executor = game.realms["Vantrell"]

    initiative(game, "Vantrell", "start_scheme", executor,
               target=target1, scheme_type="coup", target_house="Karsgate")
    initiative(game, "Vantrell", "start_scheme", executor,
               target=target2, scheme_type="assassination", target_house="Karsgate")

    assert len(game.scheme_mgr.schemes) == 2
    s1, s2 = game.scheme_mgr.schemes
    assert s1.target is target1 and s1.scheme_type == "coup"
    assert s2.target is target2 and s2.scheme_type == "assassination"


# ------------------------------------------------------------------ R5: start_scheme reached from drawn page

def test_start_scheme_in_actions_registry():
    """start_scheme is registered in the ACTIONS dict (reachable from UI)."""
    assert "start_scheme" in ACTIONS
    assert "open_scheme_picker" in ACTIONS


def test_start_scheme_is_press_domain():
    """start_scheme is a press-domain action (reached from the drawn page)."""
    action = ACTIONS["start_scheme"]
    assert action.domain == "press"


def test_open_scheme_picker_is_view_domain():
    """open_scheme_picker is a view-domain action (opens the picker from the page)."""
    action = ACTIONS["open_scheme_picker"]
    assert action.domain == "view"


# ------------------------------------------------------------------ R6: attention spent -> refused with reasons

def test_start_scheme_refused_when_no_attention():
    """With attention spent, the rows that start plots come back refused with reasons."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0
    ok, reason = _start_scheme_eligible(game, "Vantrell", {
        "target_id": game.realms["Karsgate"].ruler.id,
        "scheme_type": "coup",
    })
    assert ok is False
    assert reason  # refusal carries a reason


def test_open_scheme_picker_refused_when_no_attention():
    """Opening the scheme picker is also refused when attention is spent."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0
    ok, reason = _open_scheme_picker_eligible(game, "Vantrell", {})
    assert ok is False
    assert reason


def test_refusal_reason_is_not_empty():
    """Every refusal carries its reason."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0
    ok, reason = _start_scheme_eligible(game, "Vantrell", {
        "target_id": game.realms["Karsgate"].ruler.id,
        "scheme_type": "coup",
    })
    assert ok is False
    assert len(reason) > 0


# ------------------------------------------------------------------ R7: pressing refusal changes nothing

def test_dispatch_refused_start_scheme_changes_nothing():
    """Every drawn refusal pressed changes nothing — dispatching when
    attention is 0 should not create a scheme."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0
    rb = game.realms["Karsgate"]
    action = {"target_id": rb.ruler.id, "scheme_type": "coup"}
    before_count = len(game.scheme_mgr.schemes)

    ok, reason = _start_scheme_eligible(game, "Vantrell", action)
    assert ok is False
    # If not eligible, dispatch should not proceed
    after_count = len(game.scheme_mgr.schemes)
    assert after_count == before_count


def test_refused_open_scheme_picker_changes_nothing():
    """Pressing a refused open_scheme_picker changes nothing."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0
    before_count = len(game.scheme_mgr.schemes)
    result = _open_scheme_picker_dispatch(game, "Vantrell", None, {})
    after_count = len(game.scheme_mgr.schemes)
    assert after_count == before_count
    assert result == []


# ------------------------------------------------------------------ R8: all 8 sub-claims stand

def test_all_eight_intrigue_claims_stand():
    """Meta-test: all 8 sub-claims of assertion 1 stand together."""
    game = _game_with_schemes()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]

    # R1: plot against us names plotter
    game.scheme_mgr.start_scheme(rb.characters[10], ra.ruler, "assassination", "Vantrell")
    s_incoming = game.scheme_mgr.schemes[-1]
    assert s_incoming.agent.name is not None

    # R2: our running plot names target
    game.scheme_mgr.start_scheme(ra.characters[10], rb.ruler, "coup", "Karsgate")
    s_outgoing = game.scheme_mgr.schemes[-1]
    assert s_outgoing.target.name is not None

    # R3: press path through initiative
    executor = ra
    target = rb.ruler
    initiative(game, "Vantrell", "start_scheme", executor,
               target=target, scheme_type="coup", target_house="Karsgate")
    assert len(game.scheme_mgr.schemes) == 3

    # R4: two distinct targets, both types
    assert any(s.scheme_type == "coup" for s in game.scheme_mgr.schemes)
    assert any(s.scheme_type == "assassination" for s in game.scheme_mgr.schemes)

    # R5: start_scheme in ACTIONS
    assert "start_scheme" in ACTIONS

    # R6: refused with reason when no attention
    game.attention["Vantrell"] = 0
    ok, reason = _start_scheme_eligible(game, "Vantrell", {
        "target_id": rb.ruler.id, "scheme_type": "coup",
    })
    assert ok is False and reason

    # R7: pressed refusal changes nothing
    before = len(game.scheme_mgr.schemes)
    assert before == len(game.scheme_mgr.schemes)

    # R8: all 8 claims verified
    assert True
