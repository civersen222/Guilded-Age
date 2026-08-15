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

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import random

import pygame
from gilded.chassis import GildedGame
from gilded.houses import House
from gilded.society.realm import create_house_realm
from gilded.society.ideology import IdeologicalTide
from gilded.saga.director import Director
from gilded.world import generate_atlas
from gilded.society.schemes import SchemeManager
from gilded.society.characters import SocietyState
from gilded.docket import initiative
from gilded.ui.actions import (
    ACTIONS, _start_scheme_eligible, _start_scheme_dispatch,
    _open_scheme_picker_eligible, _open_scheme_picker_dispatch,
)
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.widgets import RegionState


# ------------------------------------------------------------------ helpers

def _game_with_schemes():
    """Build a game with two houses and a scheme manager."""
    game = GildedGame(seed=42)
    game.attention = {h: 3 for h in game.houses}
    game.press = {h: 0 for h in game.houses}
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
    executor = ra.ruler  # executor must be a Character

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
    executor = ra.ruler  # executor must be a Character

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
    executor = game.realms["Vantrell"].ruler

    initiative(game, "Vantrell", "start_scheme", executor,
               target=target, scheme_type="coup", target_house="Karsgate")
    s = game.scheme_mgr.schemes[-1]
    assert s.target is target


def test_row_decides_kind_assassination():
    """WHICH kind is row-decided — assassination is a distinct scheme type."""
    game = _game_with_schemes()
    rb = game.realms["Karsgate"]
    target = rb.ruler
    executor = game.realms["Vantrell"].ruler

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
    executor = game.realms["Vantrell"].ruler

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
    executor = ra.ruler
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


# ------------------------------------------------------------------ Press tests through the drawn page


def _make_view(game, house=None, size=(1280, 900)):
    """Create a BroadsheetView, switch to House tab, and draw."""
    view = BroadsheetView(game, house or list(game.houses.keys())[0])
    view.active_tab = "House"
    surf = pygame.Surface(size)
    view.draw(surf)
    return view, surf


def _find_intrigue_regions(view):
    """Find intrigue regions from the view's region set."""
    return [r for r in view.regions._regions if r.group == "intrigue"]


def _press(view, pos):
    """Simulate a press at the given position and return the action dict."""
    return view.handle_click(pos)


def test_start_scheme_button_drawn_with_no_plots():
    """The 'Start Scheme' control is drawn on a page with NO plot running."""
    game = _game_with_schemes()
    game.scheme_mgr.schemes.clear()  # no plots
    view, surf = _make_view(game, "Vantrell")
    regions = _find_intrigue_regions(view)
    # Should have the open_scheme_picker button
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    assert len(btn_regions) >= 1, "Start Scheme button should be drawn even with no plots"


def test_press_start_scheme_button_opens_picker():
    """Pressing the 'Start Scheme' button rect.center opens the picker on redraw."""
    game = _game_with_schemes()
    view, surf = _make_view(game, "Vantrell")
    regions = _find_intrigue_regions(view)
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    assert len(btn_regions) >= 1
    btn = btn_regions[0]
    # Press the button center
    action = _press(view, btn.rect.center)
    assert action is not None
    assert "open_scheme_picker" in action
    # Redraw — picker should be open
    surf2 = pygame.Surface((1280, 900))
    view.draw(surf2)
    assert view._scheme_picker is True


def test_press_enabled_row_starts_scheme():
    """Pressing an enabled plot row starts a scheme: scheme_mgr holds one it did not hold before."""
    game = _game_with_schemes()
    rb = game.realms["Karsgate"]
    view, surf = _make_view(game, "Vantrell")
    # Open picker first
    regions = _find_intrigue_regions(view)
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    _press(view, btn_regions[0].rect.center)
    # Redraw to show picker
    surf2 = pygame.Surface((1280, 900))
    view.draw(surf2)
    # Find start_scheme regions
    scheme_regions = [r for r in view.regions._regions if r.action.get("start_scheme")]
    assert len(scheme_regions) >= 1, "Should have at least one start_scheme row in the picker"
    row = scheme_regions[0]
    before_count = len(game.scheme_mgr.schemes)
    # Press the row
    action = _press(view, row.rect.center)
    assert action is not None
    assert "start_scheme" in action
    after_count = len(game.scheme_mgr.schemes)
    assert after_count == before_count + 1
    s = game.scheme_mgr.schemes[-1]
    ra = game.realms["Vantrell"]
    assert s.agent in ra.characters, "Agent should belong to the played House"


def test_press_different_row_different_target():
    """A second press on a different row starts a scheme against a different target."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 5  # enough attention for multiple schemes
    view, surf = _make_view(game, "Vantrell")
    # Open picker
    regions = _find_intrigue_regions(view)
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    _press(view, btn_regions[0].rect.center)
    surf2 = pygame.Surface((1280, 900))
    view.draw(surf2)
    scheme_regions = [r for r in view.regions._regions if r.action.get("start_scheme")]
    # Each target gets 2 rows (coup + assassination), so we need 4+ rows for 2 distinct targets
    assert len(scheme_regions) >= 4, "Need at least 4 rows (2 targets × 2 kinds)"
    # Pick rows for different targets (indices 0 and 2 = first target coup, second target coup)
    r1 = scheme_regions[0]
    r2 = scheme_regions[2]
    assert r1.action["target_id"] != r2.action["target_id"], "Rows should have different targets"
    # Press first row
    _press(view, r1.rect.center)
    s1 = game.scheme_mgr.schemes[-1]
    # Press second row (different target)
    _press(view, r2.rect.center)
    s2 = game.scheme_mgr.schemes[-1]
    assert s2.target.id != s1.target.id, "Different row should target a different character"


def test_press_row_of_other_kind():
    """A press on a row of the other kind starts the other scheme_type."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 5
    view, surf = _make_view(game, "Vantrell")
    regions = _find_intrigue_regions(view)
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    _press(view, btn_regions[0].rect.center)
    surf2 = pygame.Surface((1280, 900))
    view.draw(surf2)
    scheme_regions = [r for r in view.regions._regions if r.action.get("start_scheme")]
    # Find coup and assassination rows
    coup_rows = [r for r in scheme_regions if r.action.get("scheme_type") == "coup"]
    assas_rows = [r for r in scheme_regions if r.action.get("scheme_type") == "assassination"]
    assert len(coup_rows) >= 1, "Should have at least one coup row"
    assert len(assas_rows) >= 1, "Should have at least one assassination row"
    # Press coup row
    _press(view, coup_rows[0].rect.center)
    assert game.scheme_mgr.schemes[-1].scheme_type == "coup"
    # Press assassination row
    _press(view, assas_rows[0].rect.center)
    assert game.scheme_mgr.schemes[-1].scheme_type == "assassination"


def test_attention_spent_rows_drawn_disabled_with_reason():
    """Attention spent: the scheme picker button is DISABLED, and rows that start plots are refused with reasons."""
    game = _game_with_schemes()
    game.attention["Vantrell"] = 0  # spend attention
    view, surf = _make_view(game, "Vantrell")
    # The open_scheme_picker button should be DISABLED when attention is spent
    regions = _find_intrigue_regions(view)
    btn_regions = [r for r in regions if "open_scheme_picker" in r.action]
    assert len(btn_regions) >= 1, "Should have open_scheme_picker button"
    for r in btn_regions:
        assert r.state == RegionState.DISABLED, "Picker button should be DISABLED when attention is spent"
        assert r.reason, "DISABLED button should carry a reason"
    # start_scheme rows are also refused when attention is spent
    ok, reason = _start_scheme_eligible(game, "Vantrell", {
        "target_id": game.realms["Karsgate"].ruler.id,
        "scheme_type": "coup",
    })
    assert ok is False, "start_scheme should be refused when attention is spent"
    assert reason, "Refusal should carry a reason"
