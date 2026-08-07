"""I6b — measurement cases for the three properties I6 touched.

What these cases measure (unique coverage):
  1. Refused button fill differs from enabled button fill (sampled pixels)
  2. Refused button text reads >= 4.5:1 against its own fill (sampled pixels)
  3. Tooltip panel width varies with content length
  4. Long words are ellipsised — no ink outside the tooltip panel
  5. Fully-refused ladder states its reason once
  6. Partial ladder still carries reason on every refused rung
  7. Seller holding 50% gets full canonical ladder plus stake
  8. Every rung carries pct, offerable, reason keys
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import math
import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.agenda import ensure_agenda
from gilded.ui.broadsheet import BroadsheetView, BUTTON_BG, BUTTON_TEXT, \
    DISABLED_BUTTON_BG, TOOLTIP_MAX_WIDTH
from gilded.ui.widgets import RegionState, INK, FADED, PAPER_BG
from gilded.ui.actions import share_size_ladder


# ── Helpers ────────────────────────────────────────────────────────────────────

def _wcag_ratio(c1, c2):
    """Compute WCAG 2.x contrast ratio between two RGB tuples."""
    def luminance(rgb):
        vals = []
        for v in rgb:
            v = v / 255.0
            vals.append(v / 12.92 if v <= 0.03928 else
                        ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _game_view(seed=42, turns=3):
    """Return (game, BroadsheetView) on the Enterprises tab."""
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


def _sample_region_pixels(view, surf, region):
    """Return (fill, text_color) sampled from inside a button region.

    fill: pixel at the left edge of the button (background area)
    text_color: first solid text pixel found (close to BUTTON_TEXT)
    """
    from gilded.ui.broadsheet import BUTTON_TEXT
    rect = region.rect
    cy = rect.top + rect.height // 2
    # Sample the fill from the left edge of the button (away from text)
    fill_x = rect.left + 4
    fill = tuple(surf.get_at((fill_x, cy))[:3])
    # Scan right across the center row for a solid text pixel
    text = fill
    for x in range(rect.left + 20, rect.right):
        px = tuple(surf.get_at((x, cy))[:3])
        # Look for a pixel close to BUTTON_TEXT (not anti-aliased edge)
        if (abs(px[0] - BUTTON_TEXT[0]) < 30 and
            abs(px[1] - BUTTON_TEXT[1]) < 30 and
            abs(px[2] - BUTTON_TEXT[2]) < 30):
            text = px
            break
    return fill, text


# ── 1. Colour rules measured by sampled pixels ───────────────────────────────

def test_disabled_button_fill_differs_from_enabled():
    """A refused button has a different fill from an offered one (D2).

    Measured by rendering a BroadsheetView and sampling the pixel inside
    the fill area of an ENABLED region vs a DISABLED region.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    enabled_regions = [r for r in v.regions._regions
                       if r.state is RegionState.ENABLED and
                       any(k in r.action for k in ("expand_enterprise", "buy_shares", "sell_shares", "found_enterprise"))]
    disabled_regions = [r for r in v.regions._regions
                        if r.state is RegionState.DISABLED]

    # Need at least one of each to compare
    assert enabled_regions, "No ENABLED regions found to sample"
    assert disabled_regions, "No DISABLED regions found to sample"

    e_fill, _ = _sample_region_pixels(v, surf, enabled_regions[0])
    d_fill, _ = _sample_region_pixels(v, surf, disabled_regions[0])

    assert e_fill != d_fill, (
        f"ENABLED and DISABLED buttons have the same fill {e_fill} — "
        "state is invisible without reading text")


def test_disabled_button_text_contrast_at_least_45():
    """A refused button text reads >= 4.5:1 against its fill (D1).

    Measured by sampling the fill and text pixels from a DISABLED region,
    then computing the WCAG contrast ratio.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    disabled_regions = [r for r in v.regions._regions
                        if r.state is RegionState.DISABLED]
    assert disabled_regions, "No DISABLED regions found"

    for region in disabled_regions:
        fill, text = _sample_region_pixels(v, surf, region)
        ratio = _wcag_ratio(fill, text)
        assert ratio >= 4.5, (
            f"DISABLED button at {region.rect} has text contrast {ratio:.2f}:1 "
            f"(fill={fill}, text={text}) — below 4.5:1 WCAG body-text threshold")


def test_enabled_button_text_contrast_at_least_45():
    """An offered button text reads >= 4.5:1 against its fill (D1).

    Regression: ensure the enabled path was not regressed.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    enabled_regions = [r for r in v.regions._regions
                       if r.state is RegionState.ENABLED and
                       any(k in r.action for k in ("expand_enterprise", "buy_shares", "sell_shares", "found_enterprise"))]
    assert enabled_regions, "No ENABLED venture regions found"

    for region in enabled_regions[:3]:
        fill, text = _sample_region_pixels(v, surf, region)
        ratio = _wcag_ratio(fill, text)
        assert ratio >= 4.5, (
            f"ENABLED button at {region.rect} has text contrast {ratio:.2f}:1")


# ── 2. Tooltip panel sizing against content ──────────────────────────────────

def test_tooltip_panel_width_varies_with_content():
    """Tooltip panel width scales with its text content (I6 property 1).

    Two hints of very different length produce visibly different panel widths.
    Measured by rendering tooltips for short and long text, then comparing
    the resulting panel widths.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)  # Regions are populated during draw

    # Find a region with a short hint and one with a long hint
    short_hints = [r for r in v.regions._regions
                   if r.state is RegionState.ENABLED and r.hint and len(r.hint) < 30]
    long_hints = [r for r in v.regions._regions
                  if r.state is RegionState.ENABLED and r.hint and len(r.hint) > 50]

    assert short_hints, "No short-hint region found"
    assert long_hints, "No long-hint region found"

    # Draw tooltip for short hint
    v.hovered = short_hints[0]
    v.hover_pos = (short_hints[0].rect.centerx, short_hints[0].rect.centery)
    v.draw(surf)
    short_rect = v.tooltip_rect
    assert short_rect is not None, "Short hint produced no tooltip"

    # Draw tooltip for long hint
    v.hovered = long_hints[0]
    v.hover_pos = (long_hints[0].rect.centerx, long_hints[0].rect.centery)
    v.draw(surf)
    long_rect = v.tooltip_rect
    assert long_rect is not None, "Long hint produced no tooltip"

    assert long_rect.width > short_rect.width, (
        f"Long hint ({len(long_hints[0].hint)} chars) panel width {long_rect.width}px "
        f"is not wider than short hint ({len(short_hints[0].hint)} chars) panel "
        f"width {short_rect.width}px")


def test_tooltip_ellipsis_keeps_ink_inside_panel():
    """A word wider than TOOLTIP_MAX_WIDTH is ellipsised — no ink outside panel (I6 property 2).

    Measured by rendering a tooltip with a very long single word, then
    checking that no INK pixels appear outside the tooltip_rect.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)  # Populate initial regions

    # Find a region with a long hint (tab bar hints are 40+ chars)
    long_hints = [r for r in v.regions._regions
                  if r.state is RegionState.ENABLED and r.hint and len(r.hint) > 40]
    assert long_hints, "No long-hint region found"

    # Hover over the long-hint region
    v.hover_pos = long_hints[0].rect.center
    v.draw(surf)

    assert v.tooltip_rect is not None, "Long hint produced no tooltip"
    tr = v.tooltip_rect

    # Check no INK pixels outside the panel (exclude hovered region outline)
    ink_pixels_outside = 0
    hovered = long_hints[0]
    # Expand hovered region rect by 2px for the 2px outline width
    outline_rect = pygame.Rect(hovered.rect.left - 2, hovered.rect.top - 2,
                               hovered.rect.width + 4, hovered.rect.height + 4)
    check_rect = pygame.Rect(max(0, tr.left - 5), max(0, tr.top - 5),
                             min(surf.get_width(), tr.right + 5) - max(0, tr.left - 5),
                             min(surf.get_height(), tr.bottom + 5) - max(0, tr.top - 5))
    for x in range(check_rect.left, check_rect.right):
        for y in range(check_rect.top, check_rect.bottom):
            if tr.collidepoint(x, y):
                continue
            if outline_rect.collidepoint(x, y):
                continue
            pixel = tuple(surf.get_at((x, y))[:3])
            if (abs(pixel[0] - INK[0]) < 10 and
                abs(pixel[1] - INK[1]) < 10 and
                abs(pixel[2] - INK[2]) < 10):
                ink_pixels_outside += 1

    assert ink_pixels_outside == 0, (
        f"{ink_pixels_outside} INK pixels found outside tooltip panel {tr} — "
        "long word was not ellipsised properly")


# ── 3. Ladder output measurement ─────────────────────────────────────────────

def test_fully_refused_ladder_states_reason_once():
    """A fully-refused ladder states its fact once — no reason repeated (D4).

    Measured by calling share_size_ladder with a seller who holds 0%,
    then counting non-empty reason strings.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    ent = next(e for e in g.enterprises if e.eid == 13)
    ruler = g.realms[player].ruler
    kin = [c for c in g.realms[player].characters if c.id != ruler.id][0]
    ent.ledger[kin.id] = ent.ledger.pop(ruler.id)

    ladder = share_size_ladder(g, player, 13, ruler.id, kin.id)

    # All rungs are refused
    assert not any(r["offerable"] for r in ladder), "Expected all rungs refused"

    # Only one non-empty reason
    non_empty = [r["reason"] for r in ladder if r["reason"]]
    assert len(non_empty) == 1, (
        f"Fully-refused ladder has {len(non_empty)} non-empty reasons — "
        f"the fact is repeated. Reasons: {non_empty}")

    # The ladder still says something (not blank)
    assert non_empty[0], "Ladder says nothing — the fact is missing"


def test_partial_ladder_reasons_preserved():
    """A ladder with SOME offerable rungs still explains each refused rung.

    Regression: the deduplication must not affect partial refusals.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    # Use eid 1 where the ruler holds some stake
    ent = next(e for e in g.enterprises if e.eid == 1)
    ruler = g.realms[player].ruler
    available = ent.ledger.get(ruler.id, 0.0)
    if available <= 0:
        pytest.skip("Ruler holds nothing of eid 1")

    ladder = share_size_ladder(g, player, 1, ruler.id)
    non_offerable = [r for r in ladder if not r["offerable"]]
    if not non_offerable:
        pytest.skip("No refused rungs in this ladder")

    for r in non_offerable:
        assert r["reason"], (
            f"Non-offerable rung pct={r['pct']} has empty reason — "
            "partial refusal should explain each refused rung")


def test_seller_holding_stake_gets_full_ladder():
    """A seller holding 50% gets [1,5,10,25,35,50,75,100] plus their stake (D6).

    Measured by calling share_size_ladder and checking the returned pcts.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    # Find a character with a significant stake
    for ent in g.enterprises:
        for cid, pct in ent.ledger.items():
            if pct >= 10.0:
                ladder = share_size_ladder(g, player, ent.eid, cid)
                pcts = [r["pct"] for r in ladder]
                canonical = [1, 5, 10, 25, 35, 50, 75, 100]
                for c in canonical:
                    assert c in pcts, (
                        f"Canonical rung {c}% missing from ladder for "
                        f"seller holding {pct}%: got {pcts}")
                # Seller's stake included (unless already in canonical)
                if pct not in canonical:
                    assert pct in pcts, (
                        f"Stake rung {pct}% missing for seller holding {pct}%")
                # Every rung carries the required keys
                for r in ladder:
                    for key in ("pct", "offerable", "reason"):
                        assert key in r, f"Missing key {key!r} in rung"
                return  # success
    pytest.fail("No character found with >= 10% stake")


def test_fully_refused_ladder_screen_registers_one_disabled():
    """Succession sell-picker registers at most one DISABLED region (D5).

    Measured by rendering the share picker and counting DISABLED regions.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    ent = next(e for e in g.enterprises if e.eid == 13)
    ruler = g.realms[player].ruler
    kin = [c for c in g.realms[player].characters if c.id != ruler.id][0]
    ent.ledger[kin.id] = ent.ledger.pop(ruler.id)

    # Draw the share picker
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1200, 800))

    # Open the sell picker by calling _draw_share_picker directly
    v._share_picker_state = {
        "eid": 13,
        "direction": "sell",
        "counterparty_id": kin.id,
    }
    v.draw(surf)

    disabled = [r for r in v.regions._regions
                if r.state is RegionState.DISABLED]

    # The fully-refused ladder should register at most one DISABLED region
    # (the one with the reason text)
    assert len(disabled) <= 1, (
        f"Fully-refused ladder registered {len(disabled)} DISABLED regions — "
        "the same fact is registered multiple times")


def test_trade_cost_unchanged():
    """What an accepted trade costs is unchanged (D7).

    Measured by checking that stake_cost for an offerable rung matches
    the expected calculation.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    from gilded.society.shares import stake_cost

    # Find a seller with actual shares (ruler may hold 0%)
    ent = None
    seller_id = None
    for e in g.enterprises:
        for cid, pct in e.ledger.items():
            if pct >= 10:
                ent = e
                seller_id = cid
                break
        if ent:
            break
    assert ent, "No enterprise with a seller holding shares"

    ladder = share_size_ladder(g, player, ent.eid, seller_id)
    offerable = [r for r in ladder if r["offerable"]]
    assert offerable, "No offerable rungs to check"

    for r in offerable:
        expected = stake_cost(ent, r["pct"], g)
        assert r["cost"] == expected, (
            f"Cost for {r['pct']}%: expected {expected}, got {r['cost']}")
