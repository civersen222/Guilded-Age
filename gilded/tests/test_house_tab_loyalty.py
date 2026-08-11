"""Stage 5B — R-A: The loyalty NUMBER and BAND are visible for each seated man."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.society.relationships import modify_opinion
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import BAND_DISLOYAL


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_seated_loyalty_number_changes():
    """R-A: Changing a court holder's loyalty changes the tab pixels."""
    g, v = _view()
    v.active_tab = "House"
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")

    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")

    # Change the holder's loyalty
    holder.loyalty = 20.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when loyalty number changes"


def test_seated_loyalty_band_changes():
    """R-A: When loyalty crosses the threshold, band label changes."""
    g, v = _view()
    v.active_tab = "House"
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")

    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")

    # Set loyalty to disloyal level
    holder.loyalty = 10.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when loyalty band changes"


def test_band_moves_when_constant_moves():
    """R-A: If the loyalty threshold constant moves, the band label follows it."""
    g, v = _view()
    v.active_tab = "House"

    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")

    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")

    holder.loyalty = 50.0

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Move the band threshold
    import gilded.peerage as peerage_mod
    old = peerage_mod.BAND_DISLOYAL
    peerage_mod.BAND_DISLOYAL = 40.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    peerage_mod.BAND_DISLOYAL = old

    assert pixels1 != pixels2, "Pixels should change when band threshold moves"


def test_ink_affects_pixels():
    """R-A: Changing text color affects the drawn pixels."""
    g, v = _view()
    v.active_tab = "House"

    import gilded.ui.widgets as widgets_mod
    old_ink = widgets_mod.INK.copy()

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    widgets_mod.INK["text"] = pygame.Color(255, 0, 0)

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    widgets_mod.INK = old_ink

    assert pixels1 != pixels2, "Pixels should change when ink color changes"


def test_tones_bad_affects_pixels():
    """R-A: Changing tones['bad'] affects the drawn pixels."""
    g, v = _view()
    v.active_tab = "House"

    import gilded.ui.widgets as widgets_mod
    old_tones = dict(widgets_mod.TONES)

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    widgets_mod.TONES["bad"] = pygame.Color(0, 255, 0)

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    widgets_mod.TONES.update(old_tones)

    assert pixels1 != pixels2, "Pixels should change when tones['bad'] changes"


def test_type_title_affects_pixels():
    """R-A: Changing title font affects the drawn pixels."""
    g, v = _view()
    v.active_tab = "House"

    import gilded.ui.widgets as widgets_mod
    old_type = dict(widgets_mod.TYPE_TEXT) if hasattr(widgets_mod, 'TYPE_TEXT') else {}

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    if 'size' in old_type:
        widgets_mod.TYPE_TEXT['size'] = old_type['size'] + 5

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    widgets_mod.TYPE_TEXT.update(old_type)

    assert pixels1 != pixels2, "Pixels should change when font size changes"


def test_loyalty_number_affects_pixels():
    """R-A: Different loyalty values produce different pixels."""
    g, v = _view()
    v.active_tab = "House"

    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")

    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")

    holder.loyalty = 80.0
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    holder.loyalty = 20.0
    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should change when loyalty value changes"
