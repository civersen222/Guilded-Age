"""Tests for the House tab opinion display (mission I5b).

Verifies: house_lines builder exists, shows opinion + reasons, states absence
of history in words, draws without raising, pixels differ when reason differs.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame.surfarray
import random

from gilded.chassis import GildedGame
from gilded.society.characters import SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.relationships import modify_opinion, set_state
from gilded.ui.broadsheet import BroadsheetView


def _view():
    """Create a BroadsheetView with a real game."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


# ── D6: Public lines builder, called from _draw_house ──────────────────────

def test_house_lines_builder_exists():
    g, v = _view()
    lines = v.house_lines()
    assert isinstance(lines, list)
    assert len(lines) > 0


def test_house_lines_shows_court_seats():
    g, v = _view()
    lines = v.house_lines()
    # Should include treasury, ruler info, and court positions
    text = "\n".join(lines)
    assert "treasury" in text


def test_house_lines_shows_opinion_when_exists():
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")
    # Find a court holder
    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")
    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")
    # Set an opinion via modify_opinion
    set_state(g.society, {})
    modify_opinion(holder, realm.ruler, -15, "refused capital")
    lines = v.house_lines()
    text = "\n".join(lines)
    assert "opinion:" in text, f"Opinion should appear in lines: {text}"
    assert "refused capital" in text, f"Reason should appear in lines: {text}"


def test_house_lines_states_no_history():
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")
    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")
    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")
    # Direct assignment — opinion exists but no history
    pair = (holder.id, realm.ruler.id)
    g.society.opinions[pair] = -10
    lines = v.house_lines()
    text = "\n".join(lines)
    assert "no recorded history" in text, f"Should state absence of history: {text}"


def test_house_lines_vacant_seat_shows_no_number():
    g, v = _view()
    lines = v.house_lines()
    text = "\n".join(lines)
    # Vacant seats should not show opinion numbers
    for line in lines:
        if "(vacant)" in line:
            assert "opinion:" not in line, f"Vacant seat should not show opinion: {line}"


# ── D6: _draw_house calls house_lines and draws ────────────────────────────

def test_house_tab_draws_without_raising():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    v.active_tab = "House"
    v.draw(surf)  # Must not raise


def test_house_tab_drawn_pixels_differ_when_reason_changes():
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")
    holders = [h for h in realm.court.positions.values() if h is not None]
    if not holders:
        pytest.skip("No court holders")
    holder = holders[0]
    if holder.id == realm.ruler.id:
        pytest.skip("Only ruler in court")

    # Draw with one reason
    set_state(g.society, {})
    modify_opinion(holder, realm.ruler, -15, "refused capital")
    surf1 = pygame.Surface((1280, 900))
    v.active_tab = "House"
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    # Draw with a different reason
    set_state(g.society, {})
    modify_opinion(holder, realm.ruler, -15, "given a seat")
    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should differ when only the reason differs"
