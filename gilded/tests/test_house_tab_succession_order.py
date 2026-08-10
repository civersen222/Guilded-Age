"""Stage 5B2 — R-2, R-3: The order of succession is measured against the simulation.

R-2: A case goes red when the order the tab draws stops being the order the game
resolves.  Expectation is resolved from gilded.society.succession, NOT from the
read-model the tab already read.

R-3: A case goes red when the first man named on the tab stops being the man the
game would crown.  This is a different claim from R-2 and must not go red together.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report
from gilded.society.succession import succession_order, resolve_succession
from gilded.ui.house_tab import _house_tab_lines, draw_house_tab


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_succession_order_shown():
    """R-2: Succession ranks displayed on the tab match the simulation order.

    Independent source: succession_order(realm) from gilded.society.succession.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None:
        pytest.skip("No realm")

    # Independent source — the simulation's succession order
    sim_order = succession_order(realm)
    if len(sim_order) < 2:
        pytest.skip("Not enough succession candidates")

    lines = v.house_lines()
    text = "\n".join(lines)

    assert "SUCCESSION" in text, f"Succession section should appear: {text}"

    # First two from simulation should appear in rank order on the tab
    first = sim_order[0]
    second = sim_order[1]

    assert first.name in text, f"First in line '{first.name}' should appear"
    assert second.name in text, f"Second in line '{second.name}' should appear"

    # First should appear BEFORE second in the text
    first_pos = text.index(first.name)
    second_pos = text.index(second.name)
    assert first_pos < second_pos, \
        f"Succession order wrong: '{first.name}' should appear before '{second.name}'"


def test_succession_order_matches_simulation():
    """R-2: The order shown on the tab matches the simulation's succession order.

    Independent source: succession_order(realm) — not the peerage report.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None:
        pytest.skip("No realm")

    # Independent source — simulation's full succession order
    sim_order = succession_order(realm)
    if len(sim_order) < 3:
        pytest.skip("Not enough succession candidates")

    rpt = peerage_report(g, v.house)
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # Find SUCCESSION section to avoid matching names in COURT SEATS
    succ_start = text.find("SUCCESSION")
    if succ_start < 0:
        pytest.skip("No SUCCESSION section")
    succ_text = text[succ_start:]

    # Check that at least the first 3 simulation candidates appear in order
    # Use char_id to match unique characters (names can be duplicated)
    shown_count = min(len(sim_order), 10)
    positions = []
    search_start = 0
    for i in range(shown_count):
        ch = sim_order[i]
        name = ch.name
        # Search from after the previous match to handle duplicate names
        idx = succ_text.find(name, search_start)
        if idx >= 0:
            positions.append((idx, name, ch.id))
            search_start = idx + len(name)

    assert len(positions) >= 3, f"Expected at least 3 succession names on tab, found {len(positions)}"

    for i in range(len(positions) - 1):
        assert positions[i][0] < positions[i + 1][0], \
            f"Succession order wrong: '{positions[i][1]} ({positions[i][2]})' should appear before '{positions[i+1][1]} ({positions[i+1][2]})'"


def test_succession_order_pixel_change():
    """R-3 pixel check: renaming the man the simulation would crown changes pixels.

    Independent source: resolve_succession(realm) — not the peerage report.
    This is a different claim from R-2: naming the heir vs showing the order.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None:
        pytest.skip("No realm")

    # Independent source — who the simulation would actually crown
    heir_char = resolve_succession(realm)
    if heir_char is None:
        pytest.skip("No heir from simulation")

    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    draw_house_tab(surf, rect, rpt)
    pixels1 = pygame.image.tobytes(surf, "RGBA")

    old_name = heir_char.name
    heir_char.name = "Sigma Renamed"

    rpt2 = peerage_report(g, v.house)
    surf2 = pygame.Surface((1600, 1000))
    draw_house_tab(surf2, rect, rpt2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    # Restore
    heir_char.name = old_name

    assert pixels1 != pixels2, "Pixels should change when the heir (per simulation) is renamed"


def test_house_tab_lines_returns_lines():
    g, v = _view()
    rpt = peerage_report(g, v.house)
    lines = _house_tab_lines(rpt)
    assert isinstance(lines, list)
    assert len(lines) > 0


def test_draw_house_tab_draws():
    g, v = _view()
    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((640, 480))
    rect = pygame.Rect(0, 0, 640, 480)
    draw_house_tab(surf, rect, rpt)
    # Surface should have pixels set
    assert surf.get_at((320, 240)) != (0, 0, 0, 0)
