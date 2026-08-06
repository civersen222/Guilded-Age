"""I4d2b3f regression: share picker rows must not overlap."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.agenda import ensure_agenda


def _enterprises_view(seed=42, turns=0):
    """Game with agendas, advanced `turns` turns, view on Enterprises tab."""
    pygame.init()
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(turns):
        g.end_turn()
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    return g, v


def test_share_picker_rows_do_not_overlap():
    """Each counterparty row in the share picker must have a distinct y coordinate.

    Regression: rows were drawn at the same y because y was never incremented
    inside the counterparty loop."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    # Open the share picker for the first enterprise
    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid
    v._share_picker = {"direction": "buy", "eid": eid}

    v.draw(surf)

    # Collect all regions registered during picker draw
    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    assert len(picker_regions) >= 2, (
        "need at least 2 picker regions to check for overlap"
    )

    # Extract unique y coordinates — each row gets its own y
    unique_ys = set(r.rect.y for r in picker_regions)
    assert len(unique_ys) >= 3, (
        f"share picker rows overlap: only {len(unique_ys)} distinct y values "
        f"across {len(picker_regions)} regions: {sorted(unique_ys)}"
    )

    # Check that successive row bands don't overlap vertically
    # Group regions by y (each y = one row), verify each row band ends before the next begins
    row_ys = sorted(unique_ys)
    for i in range(len(row_ys) - 1):
        row_i_regions = [r for r in picker_regions if r.rect.y == row_ys[i]]
        max_bottom = max(r.rect.bottom for r in row_i_regions)
        next_y = row_ys[i + 1]
        assert next_y >= max_bottom, (
            f"share picker row at y={row_ys[i]} (bottom={max_bottom}) "
            f"overlaps next row at y={next_y}"
        )


def test_share_picker_sell_direction_rows_do_not_overlap():
    """Same overlap check for sell direction."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid
    v._share_picker = {"direction": "sell", "eid": eid}

    v.draw(surf)

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    if len(picker_regions) < 2:
        pytest.skip("not enough picker regions in sell mode")

    ys = [r.rect.y for r in picker_regions]
    unique_ys = set(ys)
    assert len(unique_ys) >= 2, (
        f"sell-mode share picker rows overlap: only {len(unique_ys)} distinct "
        f"y values across {len(picker_regions)} regions: {ys}"
    )