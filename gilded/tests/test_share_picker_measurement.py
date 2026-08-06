"""I4d2b3h — four properties the share picker has and nothing watches.

FAIL 2/3: a refused size can vanish entirely and nothing goes red.
         The mutation is: inside _draw_share_picker, a size the player cannot
         take is simply NOT DRAWN instead of drawn DISABLED. The refused rungs
         disappear from the ladder. The suite does not notice.

FAIL 4: a refused size can stop explaining itself and nothing goes red.
        The mutation: every reason and hint is replaced with a single word.
        Regions are still DISABLED but say nothing.

What these cases measure (unique coverage beyond I4d2b3g):
  1. Refused sizes are DRAWN DISABLED (not omitted) — kills the "skip refused" mutation
  2. Refused sizes are reachable via RegionSet.at() — kills the "skip refused" mutation
  3. Refused sizes explain themselves with the constraint that refused them
  4. Refused sizes carry a non-trivial hint (not just "clickable" text)
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.widgets import RegionState
from gilded.agenda import ensure_agenda


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


def test_refused_sizes_are_drawn_disabled_not_omitted():
    """Share picker draws DISABLED regions for sizes refused by the rules.

    Regression: if _draw_share_picker skips rungs where offerable is False,
    the refused sizes vanish entirely. The picker shows only affordable
    options, which lies about the shape of the choice.

    This case requires a mixed ladder (some offerable, some not). A ladder
    where everything is affordable or everything is refused cannot discriminate."""
    g, v = _enterprises_view(seed=42, turns=3)

    assert g.enterprises, "no enterprises in this seed"

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]
    enabled = [r for r in picker_regions if r.action is not None]

    # There must be at least one DISABLED region (a refused size)
    assert len(disabled) >= 1, (
        f"no DISABLED regions in share picker — if all sizes are affordable "
        f"this case measures nothing; found {len(enabled)} enabled, "
        f"{len(disabled)} disabled across {len(picker_regions)} picker regions"
    )

    # There must also be some enabled regions (affordable sizes)
    assert len(enabled) >= 1, (
        f"no enabled regions — all sizes refused; found {len(disabled)} disabled, "
        f"{len(enabled)} enabled"
    )

    # Each DISABLED region should have a hint mentioning a pct
    for r in disabled:
        assert r.hint or r.reason, (
            f"DISABLED region has no hint or reason — the refusal is silent"
        )


def test_refused_sizes_are_reachable_via_regionset_at():
    """DISABLED (refused) size buttons must be findable via regions.at().

    If a refused size is not drawn, it cannot be found at its position.
    This kills the same mutation as test_refused_sizes_are_drawn_disabled_not_omitted
    but from the reachability angle — a skipped rung is not just invisible,
    it is unfindable."""
    g, v = _enterprises_view(seed=42, turns=3)

    assert g.enterprises, "no enterprises in this seed"

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]

    assert disabled, "no DISABLED regions to check reachability for"

    # Each DISABLED region should be findable via regions.at() at its center
    found_disabled = 0
    for r in disabled:
        center = r.rect.center
        found = v.regions.at(center)
        assert found is not None, (
            f"DISABLED region at {center} is not findable via regions.at() — "
            f"refused size may have been skipped during draw"
        )
        # The found region should be the same one (same rect)
        assert found.rect == r.rect, (
            f"regions.at({center}) returned a region with rect {found.rect} "
            f"but expected {r.rect} — the DISABLED region is not at its drawn position"
        )
        found_disabled += 1

    assert found_disabled >= 1, (
        f"no DISABLED regions were reachable via regions.at() — "
        f"refused sizes may not be drawn"
    )


def test_refused_size_reason_names_the_constraint():
    """A DISABLED share picker button's reason must name the constraint that
    refused it — not just a sentinel or a single word.

    Regression: if every reason/hint is replaced with a meaningless word,
    the regions are still DISABLED but no longer explain WHAT is in the way.
    A greyed rectangle that says nothing is a silent refusal wearing a costume.

    The reason must reference the actual constraint: either the seller's
    holding limit or the buyer's affordability."""
    g, v = _enterprises_view(seed=42, turns=3)

    assert g.enterprises, "no enterprises in this seed"

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]

    assert disabled, "no DISABLED regions to check reasons for"

    for r in disabled:
        reason = r.reason or ""
        hint = r.hint or ""

        # The reason must not be a trivial sentinel
        assert reason not in ("", "X", "no", "not available", "Not available"), (
            f"DISABLED region has trivial reason '{reason}' — a refused size "
            f"must explain WHAT constraint refused it, not just say 'no'"
        )

        # The reason must name the constraint: either a holding limit or affordability
        # Valid reasons reference: "Seller only holds", "cannot afford", "treasury", "gold"
        constraint_words = ["holds", "afford", "treasury", "gold", "cannot"]
        has_constraint = any(word in reason.lower() for word in constraint_words)
        assert has_constraint, (
            f"DISABLED region reason '{reason}' does not name the constraint — "
            f"expected a reason that mentions holdings, affordability, or treasury, "
            f"not just a label"
        )

        # The hint must also carry the reason (not just "clickable" text)
        assert hint not in ("", "X", "no"), (
            f"DISABLED region hint is trivial ('{hint}') — the hint should "
            f"carry the same explanation as the reason"
        )


def test_refused_size_hint_carries_explanation():
    """A DISABLED share picker button's hint must carry the explanation
    of why it's refused — not just a trivial sentinel like 'clickable'.

    Regression: if every hint is replaced with a single word, the button
    is still greyed but no longer tells the player WHAT to do about it.
    The hint should mirror the reason."""
    g, v = _enterprises_view(seed=42, turns=3)

    assert g.enterprises, "no enterprises in this seed"

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]

    assert disabled, "no DISABLED regions to check hints for"

    found_hint = False
    for r in disabled:
        hint = r.hint or ""

        # The hint must not be a trivial sentinel
        assert hint not in ("", "X", "no", "clickable"), (
            f"DISABLED region hint is trivial ('{hint}') — "
            f"the hint should explain the refusal, not just be a label"
        )

        # The hint should reference the constraint (holding limit or affordability)
        assert any(kw in hint.lower() for kw in ("hold", "afford", "treasury", "share")), (
            f"DISABLED region hint '{hint}' does not name the constraint — "
            f"expected a hint that mentions holdings, affordability, or treasury"
        )
        found_hint = True

    assert found_hint, "no DISABLED regions had hints to check"


# ── HOLE 1: back button region exists with close_share_picker action ──────────

def test_share_picker_back_button_has_close_action():
    """The back button in the share picker carries close_share_picker action."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

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
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Find the back button hit rect
    back_hits = [h for h in v._share_picker_hits
                 if "close_share_picker" in h[1]]
    assert back_hits, "no back button found"

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
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Size buttons should have buy_shares or sell_shares in their action
    action_regions = [r for r in v.regions._regions
                      if r.action and ("buy_shares" in r.action or "sell_shares" in r.action)]
    assert len(action_regions) >= 1, (
        "share picker size buttons carry no buy_shares/sell_shares action"
    )


# ── HOLE 4: draws counterparty labels (not just sizes) ────────────────────────

def test_share_picker_draws_counterparty_labels():
    """The share picker draws counterparty labels, not just size buttons."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # The picker should have counterparty labels registered
    # Check that we have more regions than just size buttons
    picker_regions = [r for r in v.regions._regions
                      if r.group == "picker"]
    # We should have: back button + size buttons + counterparty labels
    assert len(picker_regions) >= 3, (
        "the share picker has fewer than 3 picker regions — "
        "counterparty labels may not be drawn"
    )


# ── HOLE 5: both buy and sell directions render ───────────────────────────────

def test_share_picker_both_directions_render():
    """The share picker renders correctly in both buy and sell directions."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    for direction in ("buy", "sell"):
        v._share_picker = {"direction": direction, "eid": ent.eid}
        v._share_picker_hits.clear()
        v.regions._regions.clear()
        surf = pygame.Surface((800, 600))
        v.draw(surf)

        # Must have at least a back button
        assert len(v._share_picker_hits) >= 1, (
            f"share picker in {direction} direction has fewer than 1 hit region"
        )


# ── HOLE 6: size buttons are registered as regions ────────────────────────────

def test_share_picker_size_buttons_are_regions():
    """Size buttons in the share picker are registered as regions."""
    g, v = _enterprises_view()

    ent = None
    for e in g.enterprises:
        if e.eid:
            ent = e
            break
    assert ent is not None, "no enterprises with eid"

    v._share_picker = {"direction": "buy", "eid": ent.eid}
    surf = pygame.Surface((800, 600))
    v.draw(surf)

    # Size buttons should be registered in regions
    picker_regions = [r for r in v.regions._regions
                      if r.group == "picker"]
    # At least back button + some size buttons
    assert len(picker_regions) >= 2, (
        "the share picker registered fewer than 2 picker regions — "
        "size buttons may not be registered"
    )
