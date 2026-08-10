"""Stage 5B — R-B: The disloyal kin flag appears when a man in line for succession drops below loyalty threshold."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report
from gilded.society.realm import DISLOYAL_LOYALTY


def test_disloyal_kin_flag():
    """A shareholder who becomes disloyal changes the tab pixels."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    v.active_tab = "House"

    rpt = report(g, house_name)
    # Find a shareholder (shares > 0)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Make the shareholder disloyal (below threshold)
    ch.loyalty = 10.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when a shareholder becomes disloyal"


def test_disloyal_kin_flag_moves_when_threshold_moves():
    """The flag boundary moves when DISLOYAL_LOYALTY moves.

    A shareholder at DISLOYAL_LOYALTY + 0.1 is NOT flagged.
    A shareholder at DISLOYAL_LOYALTY - 0.1 IS flagged.
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    v.active_tab = "House"

    rpt = report(g, house_name)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Just above threshold
    ch.loyalty = DISLOYAL_LOYALTY + 0.1

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Just below threshold — should change pixels
    ch.loyalty = DISLOYAL_LOYALTY - 0.1

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, (
        f"Pixels should differ when crossing loyalty threshold"
    )


def test_disloyal_kin_flag_shows_band():
    """Disloyal shareholders show a DISLOYAL band in the pixel output.

    We verify by checking that the pixel output changes when a shareholder
    goes from loyal to disloyal (the band color changes the pixels).
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    v.active_tab = "House"

    rpt = report(g, house_name)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Set loyal
    ch.loyalty = 70.0

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Set disloyal — pixels must change (band color differs)
    ch.loyalty = 15.0

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when band changes to DISLOYAL"
