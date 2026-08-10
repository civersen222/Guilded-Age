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
from gilded.peerage import report as _report
from gilded.ui.house_tab import draw_house_tab


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_seated_loyalty_number_changes():
    """R-A number case: changing a seated man's loyalty changes the displayed number."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values()
               if h is not None and h.id != realm.ruler.id]
    if not holders:
        pytest.skip("No non-ruler court holders")
    holder = holders[0]

    lines1 = v.house_lines()
    text1 = "\n".join(lines1)

    # Directly set loyalty to 30
    holder.loyalty = 30.0

    lines2 = v.house_lines()
    text2 = "\n".join(lines2)

    assert "loyalty 30" in text2, f"Loyalty number should show 30: {text2}"
    assert text1 != text2, "Lines should differ when loyalty changes"


def test_seated_loyalty_band_changes():
    """R-A band case: changing a seated man's BAND changes the displayed band.

    This tests the BAND specifically — dropping below DISLOYAL_LOYALTY (40)
    moves from DUBIOUS to DISLOYAL band.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    holders = [h for h in realm.court.positions.values()
               if h is not None and h.id != realm.ruler.id]
    if not holders:
        pytest.skip("No non-ruler court holders")
    holder = holders[0]

    lines1 = v.house_lines()
    text1 = "\n".join(lines1)

    # Set loyalty to 15 — crosses from DUBIOUS (30-50) into DISLOYAL (<40)
    holder.loyalty = 15.0

    lines2 = v.house_lines()
    text2 = "\n".join(lines2)

    assert "DISLOYAL" in text2, f"Band should show DISLOYAL: {text2}"
    assert text1 != text2, "Lines should differ when band changes"


def test_band_moves_when_constant_moves():
    """The band edge moves when DISLOYAL_LOYALTY moves (band_for uses the constant)."""
    from gilded.society.realm import DISLOYAL_LOYALTY

    # Just above the threshold should be DUBIOUS
    assert band_for(DISLOYAL_LOYALTY) == BAND_DUBIOUS
    # Just below should be DISLOYAL
    assert band_for(DISLOYAL_LOYALTY - 0.1) == BAND_DISLOYAL


def test_ink_affects_pixels():
    """Changing INK changes the rendered pixels of the house tab."""
    import gilded.ui.house_tab as ht
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    rpt = _report(g, house_name)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig_ink = ht.INK
    try:
        ht.INK = (255, 0, 0)
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        ht.INK = orig_ink

    assert pixels_before != pixels_after, "Pixels should change when INK changes"


def test_tones_bad_affects_pixels():
    """Changing TONES['bad'] changes the rendered pixels when disloyal kin are shown."""
    import gilded.ui.house_tab as ht
    from gilded.peerage import Kin, CourtReport
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]

    # Build a report, then manually add a disloyal kin to ensure "!!" lines appear
    rpt = _report(g, house_name)
    # Add a disloyal kin with shares so the !! prefix is used
    disloyal_kin = Kin(
        char_id="test_disloyal",
        name="Test Disloyal",
        age=30,
        is_alive=True,
        is_heir=False,
        succession_rank=5,
        opinion_of_ruler=0,
        loyalty=10.0,
        shares_pct=5.0,
        is_disloyal=True,
        grievances=(),
    )
    rpt = CourtReport(
        house=rpt.house,
        ruler_name=rpt.ruler_name,
        ruler_age=rpt.ruler_age,
        seats=rpt.seats,
        kin=rpt.kin + (disloyal_kin,),
        heir_designated=rpt.heir_designated,
        heir_if_ruler_died_now=rpt.heir_if_ruler_died_now,
        aggrieved_if_that_happened=rpt.aggrieved_if_that_happened,
    )

    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig_bad = ht.TONES.get("bad")
    try:
        ht.TONES["bad"] = (0, 255, 0)
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        if orig_bad is not None:
            ht.TONES["bad"] = orig_bad
        else:
            ht.TONES.pop("bad", None)

    assert pixels_before != pixels_after, "Pixels should change when TONES['bad'] changes"


def test_type_title_affects_pixels():
    """Changing TYPE_TITLE font size changes the rendered pixels."""
    import gilded.ui.house_tab as ht
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    rpt = _report(g, house_name)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig = ht.TYPE_TITLE
    try:
        ht.TYPE_TITLE = 12
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        ht.TYPE_TITLE = orig

    assert pixels_before != pixels_after, "Pixels should change when TYPE_TITLE changes"


def test_type_text_affects_pixels():
    """Changing TYPE_TEXT font size changes the rendered pixels."""
    import gilded.ui.house_tab as ht
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    rpt = _report(g, house_name)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig = ht.TYPE_TEXT
    try:
        # Use a value different from 12 (the perturbation target)
        ht.TYPE_TEXT = 8
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        ht.TYPE_TEXT = orig

    assert pixels_before != pixels_after, "Pixels should change when TYPE_TEXT changes"


def test_tones_warn_affects_pixels():
    """Changing TONES['warn'] changes the rendered pixels when dubious kin are shown."""
    import gilded.ui.house_tab as ht
    from gilded.peerage import Kin, CourtReport
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]

    rpt = _report(g, house_name)
    # Add a dubious kin (loyalty < 50, not disloyal) so the "? " prefix is used
    dubious_kin = Kin(
        char_id="test_dubious",
        name="Test Dubious",
        age=30,
        is_alive=True,
        is_heir=False,
        succession_rank=8,
        opinion_of_ruler=0,
        loyalty=35.0,
        shares_pct=0.0,
        is_disloyal=False,
        grievances=(),
    )
    rpt = CourtReport(
        house=rpt.house,
        ruler_name=rpt.ruler_name,
        ruler_age=rpt.ruler_age,
        seats=rpt.seats,
        kin=rpt.kin + (dubious_kin,),
        heir_designated=rpt.heir_designated,
        heir_if_ruler_died_now=rpt.heir_if_ruler_died_now,
        aggrieved_if_that_happened=rpt.aggrieved_if_that_happened,
    )

    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig_warn = ht.TONES.get("warn")
    try:
        ht.TONES["warn"] = (255, 0, 255)
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        if orig_warn is not None:
            ht.TONES["warn"] = orig_warn
        else:
            ht.TONES.pop("warn", None)

    assert pixels_before != pixels_after, "Pixels should change when TONES['warn'] changes"


def test_tones_good_affects_pixels():
    """Changing TONES['good'] changes the rendered pixels when the heir is shown."""
    import gilded.ui.house_tab as ht
    from gilded.peerage import Kin, CourtReport
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]

    rpt = _report(g, house_name)
    # Ensure there is an heir in the kin list
    heir_id = rpt.heir_if_ruler_died_now
    if heir_id is None:
        # Add a kin with succession_rank and set as heir
        heir_kin = Kin(
            char_id="test_heir",
            name="Test Heir",
            age=25,
            is_alive=True,
            is_heir=True,
            succession_rank=1,
            opinion_of_ruler=0,
            loyalty=70.0,
            shares_pct=0.0,
            is_disloyal=False,
            grievances=(),
        )
        rpt = CourtReport(
            house=rpt.house,
            ruler_name=rpt.ruler_name,
            ruler_age=rpt.ruler_age,
            seats=rpt.seats,
            kin=rpt.kin + (heir_kin,),
            heir_designated=rpt.heir_designated,
            heir_if_ruler_died_now="test_heir",
            aggrieved_if_that_happened=rpt.aggrieved_if_that_happened,
        )

    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    orig_good = ht.TONES.get("good")
    try:
        ht.TONES["good"] = (0, 0, 255)
        surf.fill((0, 0, 0))
        draw_house_tab(surf, rect, rpt)
        pixels_after = surf.get_buffer().raw
    finally:
        if orig_good is not None:
            ht.TONES["good"] = orig_good
        else:
            ht.TONES.pop("good", None)

    assert pixels_before != pixels_after, "Pixels should change when TONES['good'] changes"
