"""Stage 5B — DoD 9: Changing a character in a DIFFERENT house does NOT change the tab.

A surface that redraws when a rival's man changes is reading something other than this house.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.society.relationships import modify_opinion, set_state
from gilded.ui.broadsheet import BroadsheetView


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_other_house_change_no_pixel_change():
    """DoD 9: Changing a character in a DIFFERENT house does not change pixels."""
    g, v = _view()
    v.active_tab = "House"
    house_name = v.house

    # Draw the current state
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Find a character in a DIFFERENT house
    other_houses = [h for h in g.houses if h != house_name]
    if not other_houses:
        pytest.skip("Only one house")

    other_house = other_houses[0]
    other_realm = g.realms.get(other_house)
    if other_realm is None or other_realm.ruler is None:
        pytest.skip("No realm for other house")

    # Find a character in the other house
    other_chars = [c for c in other_realm.dynasty.all_characters.values()
                   if c.is_alive and c.id != other_realm.ruler.id]
    if not other_chars:
        pytest.skip("No characters in other house")

    target = other_chars[0]

    set_state(g.society, {})
    modify_opinion(target, other_realm.ruler, -20, "other house change")

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 == pixels2, \
        "Pixels should NOT change when a different house's character changes"


def test_deterministic_draw():
    """DoD 10: Drawing the same unchanged game twice produces identical pixels."""
    g, v = _view()
    v.active_tab = "House"

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 == pixels2, "Drawing the same game twice should produce identical pixels"


def test_draw_at_1024x700():
    """DoD 10: The House tab draws without raising at 1024x700."""
    g, v = _view()
    v.active_tab = "House"

    surf = pygame.Surface((1024, 700))
    v.draw(surf)  # Should not raise


def test_draw_at_1600x1000():
    """DoD 10: The House tab draws without raising at 1600x1000."""
    g, v = _view()
    v.active_tab = "House"

    surf = pygame.Surface((1600, 1000))
    v.draw(surf)  # Should not raise
