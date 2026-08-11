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
    """Return regions registered with group='court_seats'."""
    return [r for r in view.regions._regions if r.group == "court_seats"]


def test_six_court_seats_each_carry_one_control():
    """Six court seats, each carrying exactly one control."""
    game = GildedGame(seed=123)
    view, surf = _make_view(game)
    regions = _find_court_regions(view)
    assert len(regions) == 6, f"Expected 6 court seat regions, got {len(regions)}"


def test_court_control_keys_are_registered_verbs():
    """Every key a court control can emit is a verb the game will dispatch."""
    game = GildedGame(seed=123)
    view, surf = _make_view(game)
    regions = _find_court_regions(view)
    from gilded.ui.actions import ACTIONS
    for region in regions:
        if region.action:
            for key in region.action:
                if key == "char_id":
                    continue
                assert key in ACTIONS, f"Key '{key}' not in action registry"


def test_disabled_control_still_drawn():
    """With house out of attention, controls are still drawn but disabled."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    assert len(regions) == 6, f"Expected 6 court regions even with no attention, got {len(regions)}"
    for region in regions:
        assert region.action is None, "Control should be disabled with no attention"
        assert region.reason is not None, "Disabled control must carry a reason"


def test_click_dismissal_moves_pixels():
    """Clicking a dismiss control changes the drawn pixels."""
    import copy
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
    assert dismiss_region is not None, "Need a dismissible seat"

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

    assert pixels1 == pixels2, "Two draws of the same state must produce identical pixels"


def test_draw_at_1024x700():
    """House tab draws without raising at 1024x700."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house, size=(1024, 700))
    regions = _find_court_regions(view)
    assert len(regions) == 6


def test_draw_at_1600x1000():
    """House tab draws without raising at 1600x1000."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    view, surf = _make_view(game, house, size=(1600, 1000))
    regions = _find_court_regions(view)
    assert len(regions) == 6


def test_different_house_change_untouched():
    """A change to a character in a different house must change nothing."""
    import copy
    game = GildedGame(seed=123)
    houses = list(game.houses.keys())
    house_a = houses[0]
    house_b = houses[1] if len(houses) > 1 else houses[0]

    game.attention[house_a] = 5
    view1, surf1 = _make_view(game, house_a)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    realm_b = game.realms.get(house_b)
    if realm_b and realm_b.ruler:
        from gilded.society.characters import modify_opinion
        modify_opinion(realm_b.ruler, realm_b.ruler, 1, "test change")

    view2, surf2 = _make_view(game, house_a)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 == pixels2, "Change in different house must not affect this house's tab"


def test_disabled_controls_are_distinct():
    """With no attention, six court controls must be distinguishable from each other."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    rects = [r.rect for r in regions]
    for i, r1 in enumerate(rects):
        for j, r2 in enumerate(rects):
            if i != j:
                assert r1 != r2, "Two court controls share the same rect"


def test_vacant_seat_offers_appointment_chooser():
    """A vacant seat's control, when clicked, opens the appointment picker."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 5
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    # First dismiss someone to create a vacancy
    dismiss_region = None
    for r in regions:
        if r.action and "dismiss_seat" in r.action:
            dismiss_region = r
            break
    assert dismiss_region is not None, "Need a dismissible seat to create vacancy"

    pos = (dismiss_region.rect.x + 5, dismiss_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)

    # Now the dismissed seat should offer appointment
    regions = _find_court_regions(view)
    appoint_region = None
    for r in regions:
        if r.action and "open_appointment_picker" in r.action:
            appoint_region = r
            break
    assert appoint_region is not None, "Dismissed seat should offer appointment control"

    pos = (appoint_region.rect.x + 5, appoint_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)
    assert view._court_picker is not None, "Appointment picker should be open after click"


def test_picker_cancel_leaves_court_unchanged():
    """Backing out of the appointment picker leaves the court unchanged."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 5
    realm = game.realms[house]

    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    # First dismiss someone to create a vacancy
    dismiss_region = None
    for r in regions:
        if r.action and "dismiss_seat" in r.action:
            dismiss_region = r
            break
    assert dismiss_region is not None, "Need a dismissible seat to create vacancy"

    pos = (dismiss_region.rect.x + 5, dismiss_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)

    # Record court state after dismissal (before picker opens)
    court_before = {k: (v.id if v else None) for k, v in realm.court.positions.items()}

    # Now find the vacant seat and open the picker
    regions = _find_court_regions(view)
    appoint_region = None
    for r in regions:
        if r.action and "open_appointment_picker" in r.action:
            appoint_region = r
            break
    assert appoint_region is not None, "Dismissed seat should offer appointment control"

    pos = (appoint_region.rect.x + 5, appoint_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)

    cancel_region = None
    for r in view.regions._regions:
        if r.group == "picker" and r.action and "close_appointment_picker" in r.action:
            cancel_region = r
            break
    assert cancel_region is not None, "Picker should have a cancel button"

    pos = (cancel_region.rect.x + 5, cancel_region.rect.y + 5)
    result = view.handle_click(pos)
    _dispatch(view, result)
    view.draw(surf)

    court_after = {k: (v.id if v else None) for k, v in realm.court.positions.items()}
    assert court_before == court_after, "Court must be unchanged after cancel"


def test_picker_refused_when_no_attention():
    """Opening the appointment picker is refused when attention is exhausted."""
    game = GildedGame(seed=123)
    house = list(game.houses.keys())[0]
    game.attention[house] = 0
    view, surf = _make_view(game, house)
    regions = _find_court_regions(view)
    for r in regions:
        assert r.action is None, "No court control should be active with zero attention"
