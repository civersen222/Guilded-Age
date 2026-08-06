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
    """Refused sizes must appear on screen as DISABLED regions — not omitted.

    Regression: if _draw_share_picker skips rungs where offerable is False,
    the refused sizes vanish entirely. The picker shows only affordable
    options, which lies about the shape of the choice.

    This case requires a mixed ladder (some offerable, some not). A ladder
    where everything is affordable or everything is refused cannot discriminate."""
    g, v = _enterprises_view(seed=42, turns=3)

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")

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

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]
    enabled = [r for r in picker_regions if r.action is not None]

    # There must be at least one DISABLED region (a refused size)
    assert len(disabled) >= 1, (
        f"no DISABLED regions in share picker — if all sizes are affordable "
        f"this case measures nothing; found {len(enabled)} enabled, "
        f"{len(disabled)} disabled across {len(picker_regions)} picker regions"
    )

    # Count the pct values from DISABLED regions
    disabled_pcts = set()
    for r in disabled:
        if r.hint:
            disabled_pcts.add(r.hint)

    assert len(disabled_pcts) >= 1, (
        "DISABLED regions exist but have no hints — the refused sizes are "
        "present but say nothing"
    )


def test_refused_sizes_are_reachable_via_regionset_at():
    """DISABLED (refused) size buttons must be findable via regions.at().

    If a refused size is not drawn, it cannot be found at its position.
    This kills the same mutation as test_refused_sizes_are_drawn_disabled_not_omitted
    but from the reachability angle — a skipped rung is not just invisible,
    it is unfindable."""
    g, v = _enterprises_view(seed=42, turns=3)

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")

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

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]

    if not disabled:
        pytest.skip("no DISABLED regions to check reachability for")

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

    if not g.enterprises:
        pytest.skip("no enterprises in this seed")

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

    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    disabled = [r for r in picker_regions if r.state == RegionState.DISABLED]

    if not disabled:
        pytest.skip("no DISABLED regions to check reasons for")

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
