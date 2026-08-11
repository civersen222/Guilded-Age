"""Stage 5E — Heir controls on the House tab.

Tests that the House tab offers controls for designating and clearing an heir,
that the heir picker offers men in succession order with loyalty/opinion info,
and that picking/closing works correctly.
"""

import random

import pygame

from gilded.peerage import report as peerage_report
from gilded.society.characters import SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.succession import succession_order
from gilded.ui.actions import ACTIONS
from gilded.ui.house_tab import draw_house_tab
from gilded.ui.widgets import RegionState


def _make_game(seed=42, attention=3, court_verbs_used=0):
    """Build a game with a realm at the given seed."""
    rng = random.Random(seed)
    society = SocietyState(rng)
    realm = create_house_realm("Vantrell", society)

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
    game.game_over = False
    return game, realm


def _make_view(game, house):
    """Build a minimal view for drawing the House tab."""
    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = type('Regions', (), {'add': lambda self, r: None})()
    view._court_picker = None
    view._heir_picker = None
    return view


# ─── R-1: Tab offers naming ─────────────────────────────────────────────

def test_house_tab_offers_designate_heir_control():
    """The House tab draws a control that leads to designating an heir."""
    game, realm = _make_game()
    house = realm.house_name
    surface = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = Regions()
    view._court_picker = None
    view._heir_picker = None

    draw_house_tab(surface, content, rpt, view)

    # Find a region whose action leads to opening the heir picker
    heir_regions = [r for r in view.regions.items
                    if getattr(r, 'action') and 'open_heir_picker' in r.action]
    assert len(heir_regions) >= 1, "House tab must offer a control to open heir picker"


def test_designate_heir_refused_when_no_attention():
    """The designate control is refused with a reason when attention is depleted."""
    game, realm = _make_game(attention=0)
    house = realm.house_name

    # Get a living character from succession
    order = succession_order(realm)
    assert len(order) > 0, "Need at least one succession candidate"
    candidate = order[0]
    char_id = candidate["char_id"] if isinstance(candidate, dict) else candidate.id

    action = {"char_id": char_id}
    ok, reason = ACTIONS["designate_heir"].eligible(game, house, action)
    assert not ok
    assert len(reason) > 0, "Refusal must carry a readable reason"


# ─── R-2: Choice is ordered, legible, free to leave ──────────────────────

def test_heir_picker_offers_men_in_succession_order():
    """The heir picker offers men in the game's succession order, nearest throne first."""
    game, realm = _make_game()
    house = realm.house_name
    order = succession_order(realm)
    living_ids = []
    for c in order:
        if isinstance(c, dict):
            living_ids.append(c["char_id"])
        else:
            living_ids.append(c.id)
    # Remove the ruler
    ruler_id = realm.ruler.id
    living_ids = [cid for cid in living_ids if cid != ruler_id]

    assert len(living_ids) >= 10, "Need at least 10 legal heirs"

    surface = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = Regions()
    view._court_picker = None
    view._heir_picker = True  # Open the picker

    draw_house_tab(surface, content, rpt, view)

    # Collect heir picker candidate regions
    candidate_regions = [r for r in view.regions.items
                         if getattr(r, 'action') and 'char_id' in r.action
                         and 'designate_heir' in str(r.action)]
    assert len(candidate_regions) >= 10, \
        f"Heir picker must offer at least 10 candidates, got {len(candidate_regions)}"

    # Check they are in succession order
    candidate_ids = [r.action['char_id'] for r in candidate_regions]
    for i, cid in enumerate(candidate_ids):
        assert cid == living_ids[i], \
            f"Candidate {i} should be {living_ids[i]}, got {cid}"


def test_heir_picker_rows_inside_content_rect():
    """Every control drawn by the heir picker lies wholly inside the content rectangle."""
    game, realm = _make_game()
    house = realm.house_name
    surface = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = Regions()
    view._court_picker = None
    view._heir_picker = True

    draw_house_tab(surface, content, rpt, view)

    for r in view.regions.items:
        if getattr(r, 'action') and 'designate_heir' in str(r.action):
            rect = r.rect
            assert rect.left >= content.left, "Row must not extend left of content"
            assert rect.top >= content.top, "Row must not extend above content"
            assert rect.right <= content.right, "Row must not extend right of content"
            assert rect.bottom <= content.bottom, "Row must not extend below content"


def test_heir_picker_shows_loyalty_and_opinion():
    """Heir picker rows show loyalty and opinion so the player can choose between men."""
    game, realm = _make_game()
    house = realm.house_name
    surface = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = Regions()
    view._court_picker = None
    view._heir_picker = True

    draw_house_tab(surface, content, rpt, view)

    # Find candidate regions and check hint contains loyalty/opinion info
    candidate_regions = [r for r in view.regions.items
                         if getattr(r, 'action') and 'designate_heir' in str(r.action)]
    assert len(candidate_regions) > 0
    # At least one hint should mention loyalty or opinion
    hints = [r.hint for r in candidate_regions if r.hint]
    combined = ' '.join(hints).lower()
    assert 'loyalty' in combined or 'opinion' in combined, \
        "Heir picker rows must show loyalty and/or opinion information"


def test_closing_heir_picker_spends_nothing():
    """Closing the heir picker without picking spends no attention and no court action."""
    game, realm = _make_game()
    house = realm.house_name
    pre_attention = game.attention[house]
    pre_court = game.court_verbs_used

    action = {"close_heir_picker": True}
    ok, reason = ACTIONS["close_heir_picker"].eligible(game, house, action)
    assert ok, "Closing heir picker should always be eligible"

    lines = ACTIONS["close_heir_picker"].dispatch(game, house, None, action)
    assert game.attention[house] == pre_attention, \
        "Closing heir picker must not spend attention"
    assert game.court_verbs_used == pre_court, \
        "Closing heir picker must not spend court action"


# ─── R-3: Picking a man names him ────────────────────────────────────────

def test_picking_man_designates_that_man():
    """Pressing a man's row designates that specific man, not another."""
    game, realm = _make_game()
    house = realm.house_name
    order = succession_order(realm)
    ruler_id = realm.ruler.id
    living_ids = []
    for c in order:
        cid = c["char_id"] if isinstance(c, dict) else c.id
        if cid != ruler_id:
            living_ids.append(cid)

    # Pick the 5th man (index 4)
    target_id = living_ids[4]
    action = {"char_id": target_id}
    ok, reason = ACTIONS["designate_heir"].eligible(game, house, action)
    assert ok, f"Designating {target_id} should be eligible"

    lines = ACTIONS["designate_heir"].dispatch(game, house, None, action)

    # Verify the designated heir is the target
    rpt = peerage_report(game, house)
    assert rpt.heir_designated is not None, "A man should be designated"
    assert any(k.char_id == target_id and k.is_heir for k in rpt.kin), \
        f"Designated heir should be {target_id}"


def test_designating_spends_attention_and_court_action():
    """Designating an heir costs one attention and the turn's court action."""
    game, realm = _make_game(attention=3, court_verbs_used=0)
    house = realm.house_name
    order = succession_order(realm)
    candidate = order[0]
    char_id = candidate["char_id"] if isinstance(candidate, dict) else candidate.id

    action = {"char_id": char_id}
    ACTIONS["designate_heir"].dispatch(game, house, None, action)

    assert game.attention[house] == 2, "Designating should cost one attention"
    assert game.court_verbs_used == 1, "Designating should spend the court action"


# ─── R-4: Tab offers un-naming ───────────────────────────────────────────

def test_house_tab_offers_clear_heir_control():
    """The House tab draws a control that clears the heir designation."""
    game, realm = _make_game()
    house = realm.house_name
    # Designate someone first
    order = succession_order(realm)
    candidate = order[0]
    char_id = candidate["char_id"] if isinstance(candidate, dict) else candidate.id
    action = {"char_id": char_id}
    ACTIONS["designate_heir"].dispatch(game, house, None, action)

    surface = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass
    view = View()
    view.game = game
    view.house = house
    view.regions = Regions()
    view._court_picker = None
    view._heir_picker = None

    draw_house_tab(surface, content, rpt, view)

    clear_regions = [r for r in view.regions.items
                     if getattr(r, 'action') and 'clear_heir' in r.action]
    assert len(clear_regions) >= 1, "House tab must offer a control to clear heir"


def test_clear_heir_refused_when_no_designation():
    """Clear heir is refused with a reason when nobody is designated."""
    game, realm = _make_game()
    house = realm.house_name

    action = {"clear_heir": True}
    ok, reason = ACTIONS["clear_heir"].eligible(game, house, action)
    assert not ok, "Clearing heir should be refused when nobody is designated"
    assert len(reason) > 0, "Refusal must carry a readable reason"


def test_clear_heir_refused_when_no_attention():
    """Clear heir is refused when attention is depleted."""
    game, realm = _make_game(attention=0)
    house = realm.house_name
    # Designate someone first
    order = succession_order(realm)
    candidate = order[0]
    char_id = candidate["char_id"] if isinstance(candidate, dict) else candidate.id
    game2, realm2 = _make_game(attention=3)
    house2 = realm2.house_name
    ACTIONS["designate_heir"].dispatch(game2, house2, None, {"char_id": char_id})
    game2.attention[house2] = 0

    action = {"clear_heir": True}
    ok, reason = ACTIONS["clear_heir"].eligible(game2, house2, action)
    assert not ok, "Clearing heir should be refused when no attention"
    assert len(reason) > 0, "Refusal must carry a readable reason"


# ─── Additional: Tab state changes with designation ──────────────────────

def test_tab_differs_with_and_without_heir():
    """The tab drawn with a designated heir differs from the tab without one."""
    game, realm = _make_game()
    house = realm.house_name
    surface1 = pygame.Surface((640, 480))
    content = pygame.Rect(0, 0, 640, 480)
    rpt1 = peerage_report(game, house)

    class Regions:
        def __init__(self):
            self.items = []
        def add(self, region):
            self.items.append(region)

    class View:
        pass

    view1 = View()
    view1.game = game
    view1.house = house
    view1.regions = Regions()
    view1._court_picker = None
    view1._heir_picker = None
    draw_house_tab(surface1, content, rpt1, view1)

    # Now designate someone
    order = succession_order(realm)
    candidate = order[0]
    char_id = candidate["char_id"] if isinstance(candidate, dict) else candidate.id
    ACTIONS["designate_heir"].dispatch(game, house, None, {"char_id": char_id})

    surface2 = pygame.Surface((640, 480))
    rpt2 = peerage_report(game, house)
    view2 = View()
    view2.game = game
    view2.house = house
    view2.regions = Regions()
    view2._court_picker = None
    view2._heir_picker = None
    draw_house_tab(surface2, content, rpt2, view2)

   # Surfaces should differ — compare pixel arrays
    arr1 = pygame.surfarray.array3d(surface1)
    arr2 = pygame.surfarray.array3d(surface2)
    assert not (arr1 == arr2).all(), \
        "Tab should differ when a man is designated"
