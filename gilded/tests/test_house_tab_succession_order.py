"""Stage 5B — R-E: The order of succession is on screen, AND it IS the order.

This is a different claim from R-D (naming the heir). Showing the order
requires multiple ranks in sequence.
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


def test_succession_order_shown():
    """R-E: Succession ranks are displayed in order on the tab."""
    g, v = _view()
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if len(in_line) < 2:
        pytest.skip("Not enough succession ranks")

    lines = v.house_lines()
    text = "\n".join(lines)

    assert "SUCCESSION" in text, f"Succession section should appear: {text}"

    # Verify the order: first two in line should appear in rank order
    in_line.sort(key=lambda k: k.succession_rank)
    first = in_line[0]
    second = in_line[1]

    # Both names should be in the text
    assert first.name in text, f"First in line '{first.name}' should appear"
    assert second.name in text, f"Second in line '{second.name}' should appear"

    # First should appear BEFORE second in the text
    first_pos = text.index(first.name)
    second_pos = text.index(second.name)
    assert first_pos < second_pos, \
        f"Succession order wrong: '{first.name}' (rank {first.succession_rank}) should appear before '{second.name}' (rank {second.succession_rank})"


def test_succession_order_matches_simulation():
    """R-E: The order shown is the order the simulation resolves in.

    This does NOT also prove item 6 (heir name) — it checks the ORDER, not the first man.
    """
    g, v = _view()
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if len(in_line) < 3:
        pytest.skip("Not enough succession ranks")

    # Get the expected order from the report (sorted by succession_rank)
    expected_order = sorted(in_line, key=lambda k: k.succession_rank)

    lines = v.house_lines()

    # Match by "#N Name" pattern to handle duplicate names
    shown = expected_order[:10]
    positions = []
    for k in shown:
        pattern = f"#{k.succession_rank} {k.name}"
        for idx, line in enumerate(lines):
            if pattern in line:
                positions.append(idx)
                break

    # Verify they appear in order
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1], \
            f"Succession order wrong at positions {positions[i]} and {positions[i+1]}"


def test_succession_order_pixel_change():
    """R-E pixel check: changing succession changes pixels (not just heir name)."""
    g, v = _view()
    v.active_tab = "House"
    rpt = peerage_report(g, v.house)

    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    if len(in_line) < 2:
        pytest.skip("Not enough succession ranks")

    # Change the name of the SECOND in line (not the heir — different from R-D)
    second = sorted(in_line, key=lambda k: k.succession_rank)[1]
    realm = g.realms.get(v.house)
    second_char = None
    if realm:
        for ch in realm.characters:
            if ch.id == second.char_id:
                second_char = ch
                break
    if second_char is None:
        pytest.skip("Second-in-line character not found")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    old_name = second_char.name
    second_char.name = "Beta Renamed"

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    # Restore
    second_char.name = old_name

    assert pixels1 != pixels2, "Pixels should change when second-in-line is renamed"
