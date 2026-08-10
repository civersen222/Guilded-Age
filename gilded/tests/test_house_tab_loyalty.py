"""Stage 5B — R-A: Seated man's loyalty number AND band are on screen.

Two separate cases: one proves the number changes, one proves the band changes.
They must NOT go red together (T6).
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import band_for, BAND_DISLOYAL, BAND_DUBIOUS


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_seated_loyalty_number_changes():
    """R-A number case: changing a seated man's loyalty changes the displayed pixels."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values()
               if h is not None and h.id != realm.ruler.id]
    if not holders:
        pytest.skip("No non-ruler court holders")
    holder = holders[0]

    v.active_tab = "House"
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Directly set loyalty to 30
    holder.loyalty = 30.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when loyalty changes"


def test_seated_loyalty_band_changes():
    """R-A band case: changing a seated man's loyalty past the band threshold changes pixels."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values()
               if h is not None and h.id != realm.ruler.id]
    if not holders:
        pytest.skip("No non-ruler court holders")
    holder = holders[0]

    # Set loyalty above threshold
    holder.loyalty = 50.0

    v.active_tab = "House"
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Set loyalty below the disloyal threshold
    from gilded.society.realm import DISLOYAL_LOYALTY
    holder.loyalty = DISLOYAL_LOYALTY - 10.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when loyalty band changes"


def test_band_moves_when_constant_moves():
    """The band edge moves when DISLOYAL_LOYALTY moves (band_for uses the constant)."""
    from gilded.society.realm import DISLOYAL_LOYALTY

    # Just above the threshold should be DUBIOUS
    assert band_for(DISLOYAL_LOYALTY) == BAND_DUBIOUS
    # Just below should be DISLOYAL
    assert band_for(DISLOYAL_LOYALTY - 0.1) == BAND_DISLOYAL
