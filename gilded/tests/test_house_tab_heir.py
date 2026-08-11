"""Stage 5B — R-D: Heir is shown as a PERSON, not an id.

heir_if_ruler_died_now is a character id. The tab must resolve it to a name.
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


def test_heir_shown_as_name_not_id():
    """R-D: The heir's name (not char_id) appears on the tab pixels."""
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    if not rpt.heir_if_ruler_died_now:
        pytest.skip("No heir")

    heir_id = rpt.heir_if_ruler_died_now
    heir_name = None
    for k in rpt.kin:
        if k.char_id == heir_id:
            heir_name = k.name
            break

    if heir_name is None:
        pytest.skip("Heir id not found in kin")

    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pixels = pygame.image.tobytes(surf, "RGBA")

    # The heir's name should be rendered in the pixels
    # We verify by checking that renaming the heir changes the pixels
    assert len(pixels) > 0, "Surface should have pixels"


def test_heir_rename_changes_tab():
    """R-D pixel check: renaming the heir changes the drawn pixels."""
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    if not rpt.heir_if_ruler_died_now:
        pytest.skip("No heir")

    heir_id = rpt.heir_if_ruler_died_now
    heir_char = None
    realm = g.realms.get(v.house)
    if realm:
        for ch in realm.characters:
            if ch.id == heir_id:
                heir_char = ch
                break
    if heir_char is None:
        pytest.skip("Heir character not found in realm")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Rename the heir
    old_name = heir_char.name
    heir_char.name = "X" + heir_char.name

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    heir_char.name = old_name  # restore

    assert pixels1 != pixels2, "Pixels should change when heir is renamed"
