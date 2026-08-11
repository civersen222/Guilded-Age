"""Stage 5B3 — DoD 1: Pixel-level visual tests for the House tab.

The House tab is drawn to an off-screen surface and raw pixels are compared.
Nothing reads a rect, an accessor, a helper or any other name introduced by this work.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from gilded.chassis import GildedGame
from gilded.peerage import report as peerage_report
from gilded.society.characters import modify_opinion


def _draw_tab(game, house_name, size=(1280, 900)):
    """Draw the house tab to an off-screen surface and return pixel bytes."""
    rpt = peerage_report(game, house_name)
    surf = pygame.Surface(size)
    rect = pygame.Rect(0, 0, size[0], size[1])
    from gilded.ui.house_tab import draw_house_tab
    draw_house_tab(surf, rect, rpt)
    return pygame.image.tobytes(surf, "RGBA")


def test_pixel_change_on_loyalty_loss():
    """When a man of this house loses his loyalty, the pixels MUST change."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    assert realm is not None and realm.ruler is not None, "Game must have a realm with a ruler"

    pixels1 = _draw_tab(g, house_name)

    # Find a non-ruler court holder and change their loyalty
    holders = [h for h in realm.court.positions.values()
               if h is not None and h.id != realm.ruler.id]
    assert holders, "Realm must have non-ruler court holders"
    holder = holders[0]
    holder.loyalty = 10.0

    pixels2 = _draw_tab(g, house_name)
    assert pixels1 != pixels2, "Pixels must change when loyalty changes"


def test_pixel_change_on_heir_rename():
    """When the man who would inherit is renamed, the pixels MUST change."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    assert realm is not None, "Game must have a realm"

    rpt = peerage_report(g, house_name)
    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    in_line.sort(key=lambda k: k.succession_rank)
    assert in_line, "Tab should publish a line of succession"

    heir = in_line[0]
    pixels1 = _draw_tab(g, house_name)

    # Find the character and rename
    ch = None
    for c in realm.characters:
        if c.id == heir.char_id:
            ch = c
            break
    assert ch is not None, "Heir must exist in realm characters"

    ch.name = "RENAME_TEST_XYZ"
    pixels2 = _draw_tab(g, house_name)
    assert pixels1 != pixels2, "Pixels must change when heir is renamed"


def test_pixel_change_on_grievance_by_in_line_kin():
    """When a grievance is recorded by a kinsman IN LINE FOR SUCCESSION AND HOLDS NO SEAT,
    the pixels MUST change."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    assert realm is not None and realm.ruler is not None, "Game must have a realm with a ruler"

    rpt = peerage_report(g, house_name)
    # Find a kinsman in line for succession who holds no seat AND is visible on screen
    # Kin are sorted alphabetically in the tab, so pick one early in the alphabet
    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    in_line.sort(key=lambda k: k.succession_rank)
    in_line_no_seat = None
    for k in in_line:
        if k.is_alive and k.char_id != realm.ruler.id:
            # Check they hold no seat
            has_seat = False
            for s in rpt.seats:
                if not s.vacant and s.holder_id == k.char_id:
                    has_seat = True
                    break
            if not has_seat:
                in_line_no_seat = k
                break

    assert in_line_no_seat is not None, "Tab should have an in-line kin without seat"

    # Use a tall surface so all kin are rendered (72+ lines * ~20px each + header)
    pixels1 = _draw_tab(g, house_name, size=(1280, 2000))

    # Record a grievance against the ruler by this kinsman
    ch = None
    for c in realm.characters:
        if c.id == in_line_no_seat.char_id:
            ch = c
            break
    assert ch is not None, "Kin character must exist in realm"
    modify_opinion(ch, realm.ruler, -40, "grievance")

    pixels2 = _draw_tab(g, house_name, size=(1280, 2000))
    assert pixels1 != pixels2, "Pixels must change when grievance is recorded"


def test_pixel_unchanged_on_different_house_move():
    """When a character in a DIFFERENT house is moved, the pixels must NOT change."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    # Find a different house
    other_houses = [h for h in g.houses.keys() if h != house_name]
    assert other_houses, "Game must have more than one house"

    other_house = other_houses[0]
    other_realm = g.realms.get(other_house)
    assert other_realm is not None and other_realm.characters, "Other house must have characters"

    pixels1 = _draw_tab(g, house_name)

    # Change a character in the other house (rename them)
    other_char = other_realm.characters[0]
    other_char.name = "OTHER_HOUSE_RENAME_XYZ"

    pixels2 = _draw_tab(g, house_name)
    assert pixels1 == pixels2, "Pixels must NOT change when different house character changes"


def test_pixel_identical_on_double_draw():
    """When the same unchanged game is drawn twice, the pixels must be IDENTICAL."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]

    pixels1 = _draw_tab(g, house_name)
    pixels2 = _draw_tab(g, house_name)
    assert pixels1 == pixels2, "Pixels must be identical when drawing the same game twice"


def test_pixel_draw_at_1024x700():
    """The tab must draw without raising at 1024x700."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    pixels = _draw_tab(g, house_name, size=(1024, 700))
    assert len(pixels) > 0, "Tab should produce pixels at 1024x700"


def test_pixel_draw_at_1600x1000():
    """The tab must draw without raising at 1600x1000."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    pixels = _draw_tab(g, house_name, size=(1600, 1000))
    assert len(pixels) > 0, "Tab should produce pixels at 1600x1000"
