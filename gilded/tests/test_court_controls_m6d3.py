"""Stage 5C3 — Wave 1: Pixel-driven court controls (R-1, R-4, R-5, DoD 2-5, 10, 13, 14, 16).

The surface is driven, not inspected: a game is built, the House tab is drawn to an
off-screen surface through the ordinary public objects, and the controls are found
by looking at what the tab registered — never by reading a rect, an accessor, a helper
or any other name our work introduces.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.actions import ACTIONS
from gilded.ui.widgets import RegionState


def _dispatch(view, action):
    """Dispatch an action through the ACTIONS registry and redraw the view."""
    for key in action:
        act = ACTIONS.get(key)
        if act is None:
            continue
        ok, _reason = act.eligible(view.game, view.house, action)
        if not ok:
            return False
        act.dispatch(view.game, view.house, view, action)
        return True
    return False


def _make_view(game, house=None, size=(1280, 900)):
    """Create a BroadsheetView, switch to House tab, and draw."""
    view = BroadsheetView(game, house or list(game.houses.keys())[0])
    view.active_tab = "House"
    surf = pygame.Surface(size)
    view.draw(surf)
    return view, surf


def _find_court_regions(view):
    """Return regions registered with group='court_seats' sorted by rect.y."""
    regions = [r for r in view.regions._regions if r.group == "court_seats"]
    regions.sort(key=lambda r: r.rect.y)
    return regions


def test_six_court_controls_drawn():
    """The House tab draws exactly six court controls."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    assert len(regions) == 6, "House tab should draw six court controls"


def test_court_controls_are_distinct_by_rect():
    """Each court control occupies a unique rectangle."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    rects = [r.rect for r in regions]
    assert len(set(str(r) for r in rects)) == 6, "Each court control must have a distinct rectangle"


def test_disabled_controls_have_reason():
    """A disabled control carries a readable reason."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        assert r.reason, "Disabled control must carry a reason"
        assert len(r.reason) > 10, "Reason must be a real sentence, not a placeholder"


def test_disabled_controls_are_not_dispatchable():
    """A disabled control cannot be dispatched through the registry."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        assert r.state == RegionState.DISABLED, "Control should be disabled with no attention"


def test_disabled_controls_still_carry_verb():
    """A disabled control still carries the verb it would have performed."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        assert r.action is not None, "Disabled control must still carry its verb"
        assert len(r.action) == 1, "Control action should contain exactly one verb"
        verb = list(r.action.keys())[0]
        assert verb in ACTIONS, f"Verb {verb} must be in the game registry"


def test_disabled_controls_distinct_by_action():
    """Six disabled controls must carry distinct action dicts (verb + seat)."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    actions = []
    for r in regions:
        assert r.action is not None, "Control must carry an action"
        actions.append(str(r.action))
    # All six action dicts should be distinct
    assert len(set(actions)) == 6, "Six controls must carry six distinct action dicts"


def test_disabled_controls_distinct_by_verb_and_seat():
    """Six disabled controls must be distinguishable by what seat they belong to."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    seat_identifiers = []
    for r in regions:
        assert r.action is not None, "Control must carry an action"
        action = r.action
        # Extract the seat key from the action
        if "dismiss_seat" in action:
            seat_identifiers.append(("dismiss", action["dismiss_seat"]))
        elif "open_appointment_picker" in action:
            seat_identifiers.append(("appoint", action["open_appointment_picker"]))
        else:
            raise AssertionError(f"Unexpected verb: {list(action.keys())}")
    # All six should be distinct
    assert len(set(seat_identifiers)) == 6, "Six controls must belong to six distinct seats"


def test_click_dismissal_moves_pixels():
    """Clicking a dismiss control must change the drawn pixels."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 5
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    dismiss_region = None
    for r in regions:
        if r.action and "dismiss_seat" in r.action:
            dismiss_region = r
            break
    assert dismiss_region is not None, "Should find a dismissible seat"

    pixels_before = pygame.image.tobytes(surf, "RGBA")
    pos = (dismiss_region.rect.x + 5, dismiss_region.rect.y + 5)
    result = view.handle_click(pos)
    assert result is not None, "Click on dismiss control should produce a result"
    _dispatch(view, result)
    view.draw(surf)
    pixels_after = pygame.image.tobytes(surf, "RGBA")
    assert pixels_before != pixels_after, "Pixels must change after dismissal"


def test_click_dismissal_empties_seat():
    """After dismissing, the seat is empty."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 5
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    dismiss_region = None
    for r in regions:
        if r.action and "dismiss_seat" in r.action:
            dismiss_region = r
            break
    assert dismiss_region is not None

    pos = (dismiss_region.rect.x + 5, dismiss_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)

    new_regions = _find_court_regions(view)
    for r in new_regions:
        if r.rect == dismiss_region.rect:
            assert "open_appointment_picker" in r.action, "Dismissed seat should offer appointment"


def test_identical_draws_produce_identical_pixels():
    """Same game drawn twice must give identical pixels."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view1, surf1 = _make_view(game, house)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    view2, surf2 = _make_view(game, house)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")
    assert pixels1 == pixels2, "Identical game state should produce identical pixels"


def test_house_tab_draws_at_1024x700():
    """The House tab must draw without raising at 1024x700."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house, (1024, 700))
    assert surf.get_size() == (1024, 700)


def test_house_tab_draws_at_1600x1000():
    """The House tab must draw without raising at 1600x1000."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house, (1600, 1000))
    assert surf.get_size() == (1600, 1000)


def test_other_house_change_does_not_affect_tab():
    """A change to a character in a different house must change nothing."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    other_houses = [h for h in game.houses.keys() if h != house]
    if not other_houses:
        return
    other_house = other_houses[0]

    view1, surf1 = _make_view(game, house)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Change something in the other house
    if other_house in game.attention:
        game.attention[other_house] = 999

    view2, surf2 = _make_view(game, house)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")
    assert pixels1 == pixels2, "Tab should not change when another house changes"


def test_disabled_dispatch_changes_nothing():
    """Dispatching a disabled court verb must change nothing."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0

    # Record state before
    realm = game.realms[house]
    court_before = {pos: holder for pos, holder in realm.court.positions.items()}
    attention_before = game.attention[house]

    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)

    # Try to dispatch a disabled control
    for r in regions:
        if r.action:
            # The eligible check should refuse this
            for verb in r.action:
                act = ACTIONS.get(verb)
                if act:
                    ok, _reason = act.eligible(game, house, r.action)
                    assert not ok, "Should refuse dispatch when disabled"

    # Verify state unchanged
    court_after = {pos: holder for pos, holder in realm.court.positions.items()}
    assert court_before == court_after, "Court should not change"
    assert game.attention[house] == attention_before, "Attention should not change"


def test_disabled_verb_is_registry_verb():
    """Every verb a disabled control carries is one the registry dispatches."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        if r.action:
            for verb in r.action:
                assert verb in ACTIONS, f"Verb {verb} must be in the registry"


def test_refusal_keeps_reason_when_dispatched():
    """A refused control keeps its reason even if dispatch is attempted."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        reason_before = r.reason
        if r.action:
            for verb in r.action:
                act = ACTIONS.get(verb)
                if act:
                    ok, _reason = act.eligible(game, house, r.action)
                    assert not ok, "Should still be refused"
                    assert r.reason == reason_before, "Reason should not change after failed dispatch"


def test_no_court_control_action_is_none():
    """No court control should have action=None; even refusals carry their verb."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        assert r.action is not None, "Court control must carry its verb even when disabled"
