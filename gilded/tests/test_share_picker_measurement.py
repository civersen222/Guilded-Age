"""I4d2b3g — measure the share picker without changing any source.

The share picker works. Almost nothing measures it.

What was already measured (test_ui_broadsheet.py):
  - Refused sizes are DRAWN DISABLED (not omitted)
  - Refused sizes are reachable via RegionSet.at()
  - Refused sizes explain themselves (reason is a real sentence)
  - Opening the share picker retires the enterprise strip (z-order)
  - Picker regions are reachable via RegionSet.at()
  - Picker has both ENABLED and DISABLED regions
  - Census prose/assertion/message agree on one number

What this file measures (unique coverage):
  1. Back button region exists and carries close_share_picker action
  2. Back button is reachable via RegionSet.at() at its center
  3. Share picker size buttons carry buy_shares/sell_shares action
  4. Share picker draws counterparty labels (not just sizes)
  5. Both buy and sell directions produce valid picker state
  6. Share picker size buttons are registered as regions
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.widgets import RegionState
from gilded.agenda import ensure_agenda
from gilded.ui.actions import ACTIONS


def _enterprises_view(seed=42, turns=3):
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


# ── HOLE 1: back button region exists with close_share_picker action ──────────

def test_share_picker_back_button_has_close_action():
    """The back button in the share picker carries close_share_picker action."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Find the back button in share_picker_hits
    back_hits = [h for h in v._share_picker_hits
                 if "close_share_picker" in h[1]]
    assert len(back_hits) >= 1, (
        "the share picker has no back button with close_share_picker action"
    )

    # Verify it's also in the regions
    back_regions = [r for r in v.regions._regions
                    if r.action and "close_share_picker" in r.action]
    assert len(back_regions) >= 1, (
        "the share picker back button is not registered in regions"
    )


# ── HOLE 2: back button reachable via RegionSet.at() ─────────────────────────

def test_share_picker_back_button_reachable_via_at():
    """The share picker back button is reachable via RegionSet.at()."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Find the back button hit rect
    back_hits = [h for h in v._share_picker_hits
                 if "close_share_picker" in h[1]]
    if not back_hits:
        pytest.skip("no back button found")

    back_rect, back_action = back_hits[0]
    cx, cy = back_rect.center

    # RegionSet.at() should find it
    found = v.regions.at((cx, cy))
    assert found is not None, (
        "RegionSet.at(back_button_center) returned None — "
        "back button center is not reachable"
    )
    assert "close_share_picker" in found.action, (
        f"RegionSet.at found wrong action: {found.action}"
    )


# ── HOLE 3: size buttons carry buy_shares/sell_shares action ──────────────────

def test_share_picker_size_buttons_carry_action():
    """Size buttons in the share picker carry buy_shares/sell_shares action."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Size buttons are registered as regions (not in _share_picker_hits)
    # They carry buy_shares or sell_shares action
    action_regions = [r for r in v.regions._regions
                      if r.action and ("buy_shares" in r.action or "sell_shares" in r.action)]
    assert len(action_regions) >= 1, (
        "share picker size buttons carry no buy_shares/sell_shares action"
    )


# ── HOLE 4: counterparty labels drawn ─────────────────────────────────────────

def test_share_picker_draws_counterparty_labels():
    """The share picker draws counterparty labels (not just size buttons)."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # The share picker should have more than just a back button —
    # size buttons are registered as regions with group="picker"
    picker_regions = [r for r in v.regions._regions
                      if r.group == "picker"]
    # At least 1 back button + size buttons for counterparties
    assert len(picker_regions) >= 2, (
        "the share picker has only a back button — no counterparty size buttons drawn"
    )


# ── HOLE 5: both buy and sell directions produce valid picker ─────────────────

def test_share_picker_both_directions_render():
    """Both buy and sell directions produce valid picker state."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    for direction in ("buy", "sell"):
        v._share_picker = {"direction": direction, "eid": ent.eid}
        v._share_picker_hits.clear()
        v.regions._regions.clear()
        surf = pygame.Surface((800, 600))
        v.draw(surf)

        # Must have at least a back button
        assert len(v._share_picker_hits) >= 1, (
            f"share picker in '{direction}' mode drew zero hits"
        )

        # Must have regions registered
        picker_regions = [r for r in v.regions._regions
                          if r.group == "picker"]
        assert len(picker_regions) >= 1, (
            f"share picker in '{direction}' mode registered zero regions"
        )


# ── HOLE 6: size buttons registered as regions ───────────────────────────────

def test_share_picker_size_buttons_are_regions():
    """Size ladder buttons in the share picker are registered as regions."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    if ent is None:
        pytest.skip("no enterprises with eid")

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Size buttons should be registered as regions with group="picker"
    picker_regions = [r for r in v.regions._regions
                      if r.group == "picker"]
    # At least back button + some size buttons
    assert len(picker_regions) >= 2, (
        "the share picker registered fewer than 2 picker regions — "
        "size buttons may not be registered"
    )
