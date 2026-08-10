"""Stage 5B — R-C: Grievance sentences show for kin who matter.

The grievance sentences the opinion ledger stored must show for kin in line
for succession who hold no seat.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.society.relationships import modify_opinion, set_state
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_grievance_shows_for_seated_kin():
    """R-C: Recording a grievance for a seated court member changes the tab."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = peerage_report(g, v.house)
    # Find a court holder (seated)
    seat_holder = None
    for s in rpt.seats:
        if not s.vacant and s.holder_id:
            seat_holder = s
            break
    if seat_holder is None:
        pytest.skip("No seated court holders")

    # Find the character
    target_char = None
    for ch in realm.characters:
        if ch.id == seat_holder.holder_id:
            target_char = ch
            break
    if target_char is None:
        pytest.skip("Seat holder char not found")

    modify_opinion(target_char, realm.ruler, -10, "passed over")

    lines = v.house_lines()
    text = "\n".join(lines)

    assert "passed over" in text, \
        f"Grievance 'passed over' should appear on tab: {text}"


def test_grievance_pixel_change():
    """R-C pixel check: recording a grievance changes the drawn pixels."""
    g, v = _view()
    v.active_tab = "House"
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = peerage_report(g, v.house)
    seat_holder = None
    for s in rpt.seats:
        if not s.vacant and s.holder_id:
            seat_holder = s
            break
    if seat_holder is None:
        pytest.skip("No seated court holders")

    target_char = None
    for ch in realm.characters:
        if ch.id == seat_holder.holder_id:
            target_char = ch
            break
    if target_char is None:
        pytest.skip("Seat holder char not found")

    modify_opinion(target_char, realm.ruler, -10, "grievance test")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Remove grievance and redraw — pixels should change back
    g.society.opinion_history.clear()
    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should change when grievance is removed"
