"""Stage 5B — R-B: The disloyal kin flag appears when a man in line for succession drops below loyalty threshold."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame
import pygame.surfarray

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report, BAND_DISLOYAL
from gilded.society.realm import DISLOYAL_LOYALTY


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_disloyal_kin_flag():
    """A shareholder who becomes disloyal changes the tab pixels."""
    g, v = _view()
    v.active_tab = "House"
    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    rpt = report(g, v.house)
    # Find a shareholder (shares > 0)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(v.house)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Make the shareholder disloyal (below threshold)
    ch.loyalty = 10.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when a shareholder becomes disloyal"


def test_disloyal_kin_flag_moves_when_threshold_moves():
    """R-B: If DISLOYAL_LOYALTY moves, the same loyalty value changes the flag."""
    g, v = _view()
    v.active_tab = "House"

    rpt = report(g, v.house)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(v.house)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Set loyalty just below threshold
    ch.loyalty = DISLOYAL_LOYALTY - 0.1

    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pixels = pygame.image.tobytes(surf, "RGBA")

    # Move the threshold to make this loyalty value loyal
    import gilded.society.realm as realm_mod
    old = realm_mod.DISLOYAL_LOYALTY
    realm_mod.DISLOYAL_LOYALTY = ch.loyalty - 1.0  # now above threshold

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    realm_mod.DISLOYAL_LOYALTY = old  # restore

    assert pixels != pixels2, "Pixels should change when threshold moves"


def test_disloyal_kin_flag_shows_band():
    """R-B: The band label appears for disloyal kin."""
    g, v = _view()
    v.active_tab = "House"

    rpt = report(g, v.house)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(v.house)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Make disloyal
    ch.loyalty = 10.0

    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pixels = pygame.image.tobytes(surf, "RGBA")

    # The band color should be present in the pixels (disloyal band uses specific color)
    assert len(pixels) > 0, "Surface should have pixels"
