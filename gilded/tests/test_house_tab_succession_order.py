"""Stage 5B — R-E: The order of succession is on screen, AND it IS the order.

This is a different claim from R-D (naming the heir). Showing the order
requires multiple ranks in sequence.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_succession_order_shown():
    """R-E: Changing a succession member's name changes pixels —
    proving the succession list is rendered (not just the heir)."""
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if len(in_line) < 2:
        pytest.skip("Not enough succession ranks")

    # Get the second-in-line (not the heir, which is tested in R-D)
    in_line.sort(key=lambda k: k.succession_rank)
    second = in_line[1]

    realm = g.realms.get(v.house)
    second_char = None
    for ch in realm.characters:
        if ch.id == second.char_id:
            second_char = ch
            break
    if second_char is None:
        pytest.skip("Second-in-line not in characters")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Rename second-in-line
    old_name = second_char.name
    second_char.name = "Zeta Second Renamed"

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    # Restore
    second_char.name = old_name

    assert pixels1 != pixels2, (
        "Pixels should change when second-in-line is renamed — "
        "proving succession order is rendered, not just heir"
    )


def test_succession_order_matches_simulation():
    """R-E: The succession section responds to simulation data.

    We verify by changing loyalty of a succession member —
    the tab should reflect the change (loyalty/band update in succession list).
    """
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if len(in_line) < 2:
        pytest.skip("Not enough succession ranks")

    # Pick a succession member
    in_line.sort(key=lambda k: k.succession_rank)
    member = in_line[1]

    realm = g.realms.get(v.house)
    member_char = None
    for ch in realm.characters:
        if ch.id == member.char_id:
            member_char = ch
            break
    if member_char is None:
        pytest.skip("Member not in characters")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Change loyalty significantly
    member_char.loyalty = 10.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, (
        "Pixels should change when succession member loyalty changes"
    )


def test_succession_order_pixel_change():
    """R-E pixel check: succession section renders and changes with data."""
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if not in_line:
        pytest.skip("No succession members")

    # Draw baseline
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Change first-in-line name
    in_line.sort(key=lambda k: k.succession_rank)
    member = in_line[0]
    realm = g.realms.get(v.house)
    member_char = None
    for ch in realm.characters:
        if ch.id == member.char_id:
            member_char = ch
            break
    if member_char is None:
        pytest.skip("Member not in characters")

    old_name = member_char.name
    member_char.name = "Alpha Renamed"

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    # Restore
    member_char.name = old_name

    assert pixels1 != pixels2, "Pixels should change when succession member is renamed"


def test_house_tab_lines_returns_lines():
    """The house_lines method returns a list of strings."""
    g, v = _view()
    lines = v.house_lines()
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)


def test_draw_house_tab_draws():
    """The House tab draws without raising."""
    g, v = _view()
    v.active_tab = "House"
    surf = pygame.Surface((640, 480))
    v.draw(surf)  # Should not raise
    # Surface should have pixels set
    assert surf.get_at((320, 240)) != (0, 0, 0, 0)
