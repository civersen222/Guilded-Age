"""Stage 5B2 — R-1: grievances drawn for kin in line who hold no seat."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.peerage import report
from gilded.society.characters import modify_opinion
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.house_tab import draw_house_tab, _house_tab_lines


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_grievance_shown_for_succession_kin_no_seat():
    """A grievance for a succession-only kin appears in the SUCCESSION section."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    seated_ids = {s.holder_id for s in rpt.seats if not s.vacant}
    # Sort by succession rank — only first 10 are shown on the tab
    kin_no_seat = sorted([k for k in rpt.kin
                   if k.succession_rank is not None
                   and k.char_id not in seated_ids
                   and k.char_id != realm.ruler.id],
                  key=lambda k: k.succession_rank)
    # Pick one in the first 10 displayed
    kin_no_seat_top10 = [k for k in kin_no_seat if k.succession_rank <= 10]
    if not kin_no_seat_top10:
        pytest.skip("No succession kin with no seat in top 10")

    kin = kin_no_seat_top10[0]
    ch = next((c for c in realm.characters if c.id == kin.char_id), None)
    if ch is None:
        pytest.skip()

    # Record a grievance via modify_opinion (Character objects)
    modify_opinion(ch, realm.ruler, -40, "grievance")

    rpt2 = report(g, v.house)
    lines = _house_tab_lines(rpt2)
    grievance_text = "grievance"
    found = any(grievance_text.lower() in line.lower() for line in lines)
    assert found, (
        f"No grievance text for {kin.name} (rank {kin.succession_rank}) in "
        f"lines: {lines[:15]}..."
    )


def test_no_grievance_shown_when_opinion_good():
    """When opinion is neutral/positive, no grievance text appears."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    seated_ids = {s.holder_id for s in rpt.seats if not s.vacant}
    kin_no_seat = [k for k in rpt.kin
                   if k.succession_rank is not None
                   and k.char_id not in seated_ids
                   and k.char_id != realm.ruler.id]
    if not kin_no_seat:
        pytest.skip("No succession kin with no seat")

    kin = kin_no_seat[0]
    ch = next((c for c in realm.characters if c.id == kin.char_id), None)
    if ch is None:
        pytest.skip()

    # Set good opinion (no grievance reason)
    modify_opinion(ch, realm.ruler, 30, "")

    rpt2 = report(g, v.house)
    lines = _house_tab_lines(rpt2)
    grievance_text = "grievance"
    found = any(grievance_text.lower() in line.lower() for line in lines)
    assert not found, (
        f"Grievance text should not appear for {kin.name} with good opinion"
    )


def test_grievance_changes_pixels():
    """Adding a grievance for a succession kin changes the rendered output."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    seated_ids = {s.holder_id for s in rpt.seats if not s.vacant}
    kin_no_seat = sorted([k for k in rpt.kin
                   if k.succession_rank is not None
                   and k.char_id not in seated_ids
                   and k.char_id != realm.ruler.id],
                  key=lambda k: k.succession_rank)
    kin_no_seat_top10 = [k for k in kin_no_seat if k.succession_rank <= 10]
    if not kin_no_seat_top10:
        pytest.skip("No succession kin with no seat in top 10")

    kin = kin_no_seat_top10[0]
    ch = next((c for c in realm.characters if c.id == kin.char_id), None)
    if ch is None:
        pytest.skip()

    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    modify_opinion(ch, realm.ruler, -40, "grievance")
    rpt2 = report(g, v.house)
    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt2)
    pixels_after = surf.get_buffer().raw

    assert pixels_before != pixels_after, (
        f"Pixels unchanged after grievance for {kin.name} "
        f"(succession rank {kin.succession_rank})"
    )


def test_different_house_change_does_not_affect_tab():
    """Changing a character in a different house does not change the tab pixels."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_before = surf.get_buffer().raw

    other_houses = [h for h in g.houses if h != v.house]
    if other_houses:
        other_realm = g.realms.get(other_houses[0])
        if other_realm and other_realm.characters:
            ch = other_realm.characters[0]
            ch.dispositions["loyalty"] = -50.0

    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels_after = surf.get_buffer().raw

    assert pixels_before == pixels_after, (
        "Pixels changed when they shouldn't have - different house modification"
    )


def test_identical_draws_produce_identical_pixels():
    """Drawing the same report twice produces identical pixels."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels1 = surf.get_buffer().raw

    surf.fill((0, 0, 0))
    draw_house_tab(surf, rect, rpt)
    pixels2 = surf.get_buffer().raw

    assert pixels1 == pixels2, "Identical draws should produce identical pixels"


def test_tab_draws_at_1024x700():
    """House tab draws without raising at 1024x700."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    surf = pygame.Surface((1024, 700))
    rect = pygame.Rect(0, 0, 1024, 700)

    draw_house_tab(surf, rect, rpt)


def test_tab_draws_at_1600x1000():
    """House tab draws without raising at 1600x1000."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = report(g, v.house)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    draw_house_tab(surf, rect, rpt)
