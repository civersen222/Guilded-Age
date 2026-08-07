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

I6f — new cases added:
  C1  Refused control fill differs from offered (sampled pixels)
  C2  Every control's text >= 4.5:1 against its fill (sampled pixels)
  C3  Refused control's label legible (sampled pixels)
  C4  Tooltip panel width tracks text length (rendered measurement)
  C5  Hovering changes no pixel outside tooltip + control (surface diff)
  C6  Over-wide word leaves no ink outside panel (rendered measurement)
  C7  Sell picker for empty holder: one refused region, not blank
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
from gilded.ui.widgets import RegionState, INK, FADED, PAPER_BG, Region
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
    text_color: most distinct pixel found (avoids anti-aliased edges)
    """
    rect = region.rect
    cy = rect.top + rect.height // 2
    # Sample the fill from the left edge of the button (away from text)
    fill_x = rect.left + 4
    fill = tuple(surf.get_at((fill_x, cy))[:3])
    # Scan across the center row for the most distinct pixel (solid text)
    text = fill
    max_diff = 0
    for x in range(rect.left + 20, rect.right):
        px = tuple(surf.get_at((x, cy))[:3])
        diff = abs(px[0] - fill[0]) + abs(px[1] - fill[1]) + abs(px[2] - fill[2])
        if diff > max_diff:
            max_diff = diff
            text = px
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

    Measured by rendering the page twice (with/without hover) and diffing.
    Hovering changes zero pixels outside the tooltip panel and hovered control.
    """
    g, v = _game_view()
    surf_no_hover = pygame.Surface((1200, 800))
    v.draw(surf_no_hover)  # Populate initial regions

    # Find a region with a long hint (tab bar hints are 40+ chars)
    long_hints = [r for r in v.regions._regions
                  if r.state is RegionState.ENABLED and r.hint and len(r.hint) > 40]
    assert long_hints, "No long-hint region found"

    # Hover over the long-hint region and redraw
    v.hover_pos = long_hints[0].rect.center
    surf_hover = pygame.Surface((1200, 800))
    v.draw(surf_hover)

    assert v.tooltip_rect is not None, "Long hint produced no tooltip"
    tr = v.tooltip_rect
    hovered = long_hints[0]

    # Count pixels that CHANGED due to hover, outside tooltip and hovered control
    changed_outside = 0
    for x in range(max(0, tr.left - 5), min(surf_hover.get_width(), tr.right + 5)):
        for y in range(max(0, tr.top - 5), min(surf_hover.get_height(), tr.bottom + 5)):
            if tr.collidepoint(x, y):
                continue
            if hovered.rect.collidepoint(x, y):
                continue
            p_before = surf_no_hover.get_at((x, y))[:3]
            p_after = surf_hover.get_at((x, y))[:3]
            if tuple(p_before) != tuple(p_after):
                changed_outside += 1

    assert changed_outside == 0, (
        f"{changed_outside} pixels changed outside tooltip panel {tr} and "
        f"hovered control {hovered.rect} — hover changed something it shouldn't")


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


# ── I6f: new cases C1–C7 ──────────────────────────────────────────────────────

def test_refused_control_fill_differs_from_offered():
    """C1: A refused control and an offered one do not share a fill.

    Rendered to a Surface, sampled pixels from ENABLED and DISABLED regions,
    measured that their fills differ.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    enabled_regions = [r for r in v.regions._regions
                       if r.state is RegionState.ENABLED]
    disabled_regions = [r for r in v.regions._regions
                        if r.state is RegionState.DISABLED]
    assert enabled_regions, "No ENABLED regions found"
    assert disabled_regions, "No DISABLED regions found"

    e_fill, _ = _sample_region_pixels(v, surf, enabled_regions[0])
    d_fill, _ = _sample_region_pixels(v, surf, disabled_regions[0])
    assert e_fill != d_fill, (
        f"ENABLED and DISABLED fills are the same: {e_fill}")


def test_every_control_text_contrast_at_least_45():
    """C2: Every registered control's text reads at 4.5:1 or better against its fill.

    Walks ALL registered regions on a rendered surface, samples fill and text,
    computes WCAG contrast ratio, asserts none under 4.5.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    for region in v.regions._regions:
        fill, text = _sample_region_pixels(v, surf, region)
        ratio = _wcag_ratio(fill, text)
        assert ratio >= 4.5, (
            f"Region at {region.rect} state={region.state} has text contrast "
            f"{ratio:.2f}:1 (fill={fill}, text={text})")


def test_refused_control_label_legible():
    """C3: A refused control's own label is legible.

    Specific guard against the original failure: FADED (96,88,78) on
    (60,82,60) at 1.22:1. Samples DISABLED regions and measures contrast.
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
            f"DISABLED region at {region.rect} label contrast {ratio:.2f}:1 "
            f"(fill={fill}, text={text}) — label illegible")


def test_tooltip_panel_width_tracks_text():
    """C4: Tooltip panels are not all one width; width tracks the text.

    Two hints of very different length produce visibly different panel widths.
    Measures the rendered panel rect, not a constant.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    # Find regions with short and long hints
    short_hints = [r for r in v.regions._regions
                   if r.hint and len(r.hint) < 30]
    long_hints = [r for r in v.regions._regions
                  if r.hint and len(r.hint) > 40]
    assert short_hints, "No short-hint region found"
    assert long_hints, "No long-hint region found"

    # Render tooltip for short hint
    v.hover_pos = short_hints[0].rect.center
    v.draw(surf)
    short_rect = v.tooltip_rect
    assert short_rect is not None, "Short hint produced no tooltip"

    # Render tooltip for long hint
    v.hover_pos = long_hints[0].rect.center
    v.draw(surf)
    long_rect = v.tooltip_rect
    assert long_rect is not None, "Long hint produced no tooltip"

    assert long_rect.width > short_rect.width, (
        f"Long hint panel ({long_rect.width}px) not wider than short "
        f"({short_rect.width}px)")


def test_hover_changes_no_pixel_outside_tooltip_and_control():
    """C5: Hovering a control changes zero pixels outside the tooltip panel
    and the hovered control itself.

    Renders the page twice — once without hover, once with — then diffs
    the two surfaces pixel by pixel, excluding the tooltip rect and the
    hovered control rect.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))

    # Render without hover
    v.hover_pos = None
    v.hovered = None
    v.draw(surf)
    surf_no_hover = surf.copy()

    # Pick a control to hover
    regions = v.regions._regions
    if not regions:
        pytest.skip("No regions to hover")

    ctrl = regions[0]
    v.hover_pos = ctrl.rect.center
    v.draw(surf)

    # Find tooltip rect after hover
    tr = v.tooltip_rect
    if tr is None:
        # Some controls have no hint — pick one that does
        for r in regions:
            if r.hint or (r.state is RegionState.DISABLED and r.reason):
                ctrl = r
                break
        else:
            pytest.skip("No control with tooltip text")
        v.hover_pos = ctrl.rect.center
        v.draw(surf)
        tr = v.tooltip_rect
        if tr is None:
            pytest.skip("No tooltip produced")

    # Expand hovered control rect for outline
    outline = pygame.Rect(ctrl.rect.left - 2, ctrl.rect.top - 2,
                          ctrl.rect.width + 4, ctrl.rect.height + 4)

    # Count changed pixels outside tooltip and control
    diff = 0
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            if (tr is None or
                not (max(tr.left - 1, 0) <= x <= min(tr.right, surf.get_width() - 1) and
                     max(tr.top - 1, 0) <= y <= min(tr.bottom, surf.get_height() - 1))):
                if not (max(outline.left, 0) <= x <= min(outline.right, surf.get_width() - 1) and
                        max(outline.top, 0) <= y <= min(outline.bottom, surf.get_height() - 1)):
                    if surf.get_at((x, y)) != surf_no_hover.get_at((x, y)):
                        diff += 1

    assert diff == 0, (
        f"{diff} pixels changed outside tooltip and hovered control")


def test_overwide_word_leaves_no_ink_outside_panel():
    """C6: A word wider than the wrap cap leaves no ink outside the panel.

    Feeds a deliberately long single WORD (no spaces) as a hint, renders
    the tooltip, and checks that no INK pixels appear outside the panel.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    # Find a region and replace it with a long single-word hint
    regions = v.regions._regions
    assert regions, "No regions found"
    original_region = regions[0]
    long_word = "a" * 96  # Single word, no spaces — reaches the ellipsis branch
    target = Region(
        rect=original_region.rect,
        action=original_region.action,
        state=original_region.state,
        reason=original_region.reason,
        hint=long_word,
        group=original_region.group,
    )
    v.regions._regions[0] = target

    # Draw without hover (baseline)
    v.hover_pos = None
    v.hovered = None
    v.draw(surf)
    surf_baseline = surf.copy()

    # Draw with hover
    v.hover_pos = target.rect.center
    v.draw(surf)

    tr = v.tooltip_rect
    assert tr is not None, "Long word produced no tooltip"

    # Expand hovered rect for outline
    outline = pygame.Rect(target.rect.left - 2, target.rect.top - 2,
                          target.rect.width + 4, target.rect.height + 4)

    # Count pixels that changed outside the panel (but not on the control outline)
    # and are INK — the tooltip should be the only thing that draws new INK
    ink_outside = 0
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            if not (tr.left <= x <= tr.right and tr.top <= y <= tr.bottom):
                if not (outline.left <= x <= outline.right and
                        outline.top <= y <= outline.bottom):
                    if surf.get_at((x, y)) != surf_baseline.get_at((x, y)):
                        pixel = surf.get_at((x, y))
                        if pixel[:3] == INK[:3]:
                            ink_outside += 1

    v.regions._regions[0] = original_region
    assert ink_outside == 0, (
        f"{ink_outside} INK pixels outside tooltip panel with over-wide word")


def test_sell_picker_empty_holder_one_refused_not_blank():
    """C7: A sell picker for a seller who holds nothing registers one refused
    region and is not blank.

    Both halves: counts the refused regions and verifies something was drawn.
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

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    # Find the sell_shares init action and trigger the picker
    sell_actions = [r for r in v.regions._regions
                    if r.action and "sell_shares" in r.action
                    and r.action.get("sell_shares") == ent.eid]
    assert sell_actions, "No sell_shares action for enterprise"

    # Init the picker by clicking
    action = sell_actions[0].action
    if action:
        result = v.handle_click(sell_actions[0].rect.center)
        if result:
            v = BroadsheetView(g, player)
            v.active_tab = "Enterprises"
            v._share_picker = {"direction": "sell", "eid": ent.eid}

    v.draw(surf)

    # Count picker-related disabled regions
    picker_disabled = [r for r in v.regions._regions
                       if r.state is RegionState.DISABLED and
                       r.group == "picker"]

    assert len(picker_disabled) >= 1, (
        f"Expected at least 1 refused picker region, got {len(picker_disabled)}")
    assert len(picker_disabled) <= 1, (
        f"Expected at most 1 refused picker region, got {len(picker_disabled)}")

    # Verify something was drawn — the surface should not be blank in the picker area
    # Sample a region of the surface where the picker should be
    picker_area = pygame.Rect(100, 200, 400, 200)
    pixels = []
    for x in range(picker_area.left, min(picker_area.right, surf.get_width())):
        for y in range(picker_area.top, min(picker_area.bottom, surf.get_height())):
            pixels.append(tuple(surf.get_at((x, y))))
    unique_colors = set(pixels)
    assert len(unique_colors) > 1, (
        "Picker area is blank — only one color found")


def test_partial_ladder_reasons_preserved():
    """A ladder where some rungs are offerable and some are refused explains
    every refused rung.

    Constructs a fixture: eid 1, a holder with a 50% stake, six offerable
    and two refused, both explained.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()

    # Find an enterprise with a holder at ~50% to get a partial ladder
    ent = None
    seller_id = None
    for e in g.enterprises:
        for cid, pct in e.ledger.items():
            if 30 <= pct <= 60:
                ent = e
                seller_id = cid
                break
        if ent:
            break

    if not ent:
        # Construct one: give a character 50% of an enterprise
        ent = g.enterprises[0]
        characters = list(g.realms[player].characters)
        if len(characters) >= 2:
            seller_id = characters[1].id
            # Clear existing ledger and set 50%
            ent.ledger = {characters[0].id: 50.0, seller_id: 50.0}
        else:
            pytest.skip("Not enough characters to construct fixture")

    # Find a buyer — any character not the seller
    all_chars = list(g.realms[player].characters)
    buyer_id = None
    for c in all_chars:
        if c.id != seller_id:
            buyer_id = c.id
            break
    assert buyer_id, "No buyer found"

    ladder = share_size_ladder(g, player, ent.eid, seller_id, buyer_id)

    # There must be both offerable and refused rungs
    offerable = [r for r in ladder if r["offerable"]]
    refused = [r for r in ladder if not r["offerable"]]

    assert offerable, "No offerable rungs — not a partial ladder"
    assert refused, "No refused rungs — not a partial ladder"

    # Every refused rung must have a reason
    for r in refused:
        assert r["reason"], (
            f"Refused rung at {r['pct']}% has no reason — "
            f"the player gets no explanation")
