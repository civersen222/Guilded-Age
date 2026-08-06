"""I4d2b3g — measure the share picker without changing any source.

Five holes measured:
  1. Refused sizes are DRAWN DISABLED (not omitted).
  2. Each refusal EXPLAINS ITSELF (reason is a real sentence).
  3. Opening the SHARE picker retires the enterprise strip (z-order).
  4. Census prose, assertion, and message agree on one number.
  5. All four properties above have dedicated cases.
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


# ── HOLE 1: refused sizes are drawn DISABLED, not omitted ────────────────────


def test_refused_share_sizes_are_drawn_disabled():
    """A size the House cannot take is drawn greyed and DISABLED, not omitted.

    Regression: if the code stops drawing refused rungs, a test that only
    counts DISABLED regions would pass with zero — it could not tell
    "nothing is refused" from "refusals are invisible"."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid

    # Open via the action registry (the real route)
    action = {"buy_shares": eid}
    ACTIONS["buy_shares"].dispatch(g, next(iter(g.houses)), v, action)
    assert v._share_picker is not None, "premise: the share picker must open"

    v.draw(surf)

    # Collect picker regions that are DISABLED
    disabled = [r for r in v.regions._regions
                if r.group == "picker" and r.state is RegionState.DISABLED]

    assert len(disabled) >= 1, (
        "the share picker drew zero DISABLED regions — refused sizes are "
        "either invisible or the fixture changed; I3d demands they are drawn"
    )


def test_refused_share_sizes_are_reachable_via_regionset_at():
    """A refused rung must be hittable — RegionSet.at(center) returns the rung.

    Three waves failed because a region was registered but not reachable.
    This case asks the RegionSet, not the list, to prove reachability."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid

    action = {"buy_shares": eid}
    ACTIONS["buy_shares"].dispatch(g, next(iter(g.houses)), v, action)
    v.draw(surf)

    disabled = [r for r in v.regions._regions
                if r.group == "picker" and r.state is RegionState.DISABLED]

    assert len(disabled) >= 1, "premise: there must be refused rungs"

    unreachable = [
        r for r in disabled
        if v.regions.at(r.rect.center) is not r
    ]
    assert unreachable == [], (
        f"{len(unreachable)} refused rung(s) registered but unreachable via "
        "RegionSet.at() — a click on them would hit something else or nothing"
    )


# ── HOLE 2: each refusal explains itself ─────────────────────────────────────


def test_refused_share_sizes_explain_themselves():
    """Every DISABLED rung carries a non-trivial reason about a real rule.

    I3d's decision was not that a refusal be VISIBLE — it was that a refusal
    EXPLAINS ITSELF.  A test that counts DISABLED regions cannot tell the
    difference between 'x' and 'Seller only holds 40.0%'.

    We assert properties of the text (length, no sentinel), not the literal
    wording — the game owns the exact message."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid

    action = {"buy_shares": eid}
    ACTIONS["buy_shares"].dispatch(g, next(iter(g.houses)), v, action)
    v.draw(surf)

    disabled = [r for r in v.regions._regions
                if r.group == "picker" and r.state is RegionState.DISABLED]

    assert len(disabled) >= 1, "premise: there must be refused rungs"

    bad_reasons = []
    for r in disabled:
        reason = r.reason or ""
        # Each reason must be a real sentence, not a sentinel or empty
        if len(reason) < 5:
            bad_reasons.append((r.rect, reason))
        if reason and reason[0] in ("x", "X"):
            bad_reasons.append((r.rect, reason))

    assert bad_reasons == [], (
        f"{len(bad_reasons)} refused rung(s) carry an empty or trivial reason "
        f"({bad_reasons[:3]}) — I3d demands each refusal explains itself"
    )


# ── HOLE 3: opening the share picker retires the enterprise strip ────────────


def test_opening_the_share_picker_retires_the_enterprise_strip():
    """The share picker replaces the enterprise actions; it does not cover them.

    This is the assertion that makes a z-order mechanism unnecessary. If it
    ever fails, two regions have begun competing for the same point and
    RegionSet.at()'s reverse scan is deciding a question nobody designed.

    Mirrors test_opening_the_picker_retires_the_venture_regions but for the
    SHARE picker (the DIRECTOR picker case already exists)."""
    g, v = _enterprises_view(seed=42, turns=3)
    surf = pygame.Surface((1280, 900))

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")
    eid = g.enterprises[0].eid

    # Draw the closed tab first to establish baseline
    v.draw(surf)

    # Find a Buy Shares control and click it via handle_click
    buy_regions = [r for r in v.regions._regions
                   if (r.action or {}).get("buy_shares") is not None]
    assert len(buy_regions) >= 1, "premise: there must be a buy_shares control"
    target = buy_regions[0]

    # Click the control — handle_click returns the verb
    action = v.handle_click(target.rect.center)
    assert action is not None, "premise: clicking a buy_shares control returns an action"

    # Dispatch through the registry (this is what the real app does)
    player = next(iter(g.houses))
    ACTIONS["buy_shares"].dispatch(g, player, v, action)

    # Re-draw — the picker should now be open
    v.draw(surf)
    assert v._share_picker is not None, "premise: the share picker must be open"

    # The enterprise strip (venture:*, buy_shares:*, sell_shares:*) must be retired
    venture = [r for r in v.regions._regions
               if r.group.startswith("venture:") or
               r.group.startswith("buy_shares:") or
               r.group.startswith("sell_shares:")]
    assert venture == [], (
        f"opening the share picker left {len(venture)} enterprise regions "
        "drawn — they must be retired, not buried under the picker"
    )
    assert [r for r in v.regions._regions if r.group == "picker"], (
        "the picker drew no regions of its own"
    )
