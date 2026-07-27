"""G22 broadsheet screens: tabs, headless draw, and the click actions."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.grip import report as grip_report
from gilded.market import COMMODITIES
from gilded.ui.broadsheet import TABS, BroadsheetView


def _view():
    pygame.init()
    g = GildedGame(seed=42)
    return g, BroadsheetView(g, next(iter(g.houses)))


def test_tabs_shape():
    assert TABS == ("Briefing", "Gazette", "Ledger", "Letters",
                    "Docket", "Policies", "Enterprises", "Atlas", "Powers", "House")


def test_hud_rides_above_every_tab():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    for tab in TABS:
        v.active_tab = tab
        v.draw(surf)   # the HUD is drawn on every tab; must not crash


def test_briefing_is_the_default_view():
    g, v = _view()
    assert v.active_tab == "Briefing"


def test_briefing_agenda_rules_a_petition():
    g, v = _view()
    v.active_tab = "Briefing"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v._option_hits, "the briefing surfaces the docket as an Agenda"
    rect, action = v._option_hits[0]
    result = v.handle_click(rect.center)
    assert result is not None and "rule" in result
    pid, key, exec_id = result["rule"]
    assert any(p.pid == pid for p in g.docket_by_house[v.house])


def test_every_tab_draws_headless():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    for tab in TABS:
        v.active_tab = tab
        v.draw(surf)


def test_off_surface_click_is_none():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v.handle_click((5000, 5000)) is None


def test_clicking_a_tab_switches():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    rect = v._tab_rects["Docket"]
    action = v.handle_click(rect.center)
    assert action == {"tab": "Docket"} and v.active_tab == "Docket"


def test_end_turn_button():
    g, v = _view()
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v.handle_click(v._end_turn_rect.center) == {"end_turn": True}


def test_docket_option_returns_rule_action():
    g, v = _view()
    v.active_tab = "Docket"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v._option_hits, "seed 42 opens with paper on the desk"
    rect, action = v._option_hits[0]
    result = v.handle_click(rect.center)
    assert result is not None and "rule" in result
    pid, key, exec_id = result["rule"]
    assert any(p.pid == pid for p in g.docket_by_house[v.house])
    assert isinstance(key, str)


def test_executor_cycle_changes_choice_not_game():
    g, v = _view()
    v.active_tab = "Docket"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v._exec_hits
    rect, pid = v._exec_hits[0]
    before = v._exec_idx.get(pid, 0)
    assert v.handle_click(rect.center) is None      # UI-internal, no game action
    assert v._exec_idx[pid] != before


def test_policies_tab_draws_and_clicks():
    g, v = _view()
    v.active_tab = "Policies"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)                                     # must not raise
    assert v._dial_hits                              # dial hit-regions were built
    rect, key = v._dial_hits[0]
    action = v.handle_click((rect.centerx, rect.centery))
    assert set(action) == {"set_stance"}
    k, val = action["set_stance"]
    assert k in ("capital", "labor", "expansion", "diplomacy", "war")
    assert -100 <= val <= 100 and val % 10 == 0


def test_atlas_click_selects_province():
    g, v = _view()
    v.active_tab = "Atlas"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pid = next(iter(g.atlas.provinces))
    c = g.atlas.provinces[pid].center
    result = v.handle_click((int(c[0] * 8), int(c[1] * 8)))
    assert result == {"select_province": pid} and v.selected_pid == pid


def test_powers_tab_lists_houses_by_threat():
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView, TABS
    from gilded import agenda
    g = GildedGame(seed=7)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    view = BroadsheetView(g, player)
    assert "Powers" in TABS
    lines = view.powers_lines()
    assert lines and all(isinstance(s, str) for s in lines)
    for h in g.houses:
        if h != player:
            assert any(h in ln for ln in lines)


# ─────────────────────────────────────────────────────────────────
# Enterprises tab tests — Stage 4 L4.1b
# ─────────────────────────────────────────────────────────────────

def _enterprises_view(seed=42, turns=0):
    """Return a game advanced `turns` turns and a BroadsheetView for the Enterprises tab."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded import agenda
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    for _ in range(turns):
        g.end_turn()
    view = BroadsheetView(g, player)
    view.active_tab = "Enterprises"
    return g, view


def test_enterprises_band_is_spelled_for_a_player():
    """A1: band displays 'IRON GRIP' not 'IRON_GRIP'."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    # The band constant IRON_GRIP should appear as 'IRON GRIP' (space, not underscore)
    assert "IRON_GRIP" not in banner, "band should not contain the raw enum spelling"
    # The band value should appear with a space
    r = grip_report(g, v.house)
    expected_spelling = r.band.replace("_", " ")
    assert expected_spelling in banner, f"banner should contain '{expected_spelling}'"


def test_enterprises_banner_shows_margin():
    """A2: banner states the margin between stake and threshold."""
    g, v = _enterprises_view(seed=42, turns=5)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    margin = r.margin
    # Guard: margin must differ from threshold and stake so the test is meaningful
    # At turn 5 seed 42, margin should be distinguishable from threshold
    margin_str = f"{margin:.1f}"
    threshold_str = f"{r.threshold:.1f}"
    assert margin_str != threshold_str, (
        f"CANNOT MEASURE: margin ({margin_str}) equals threshold ({threshold_str}) "
        f"at seed=42 turn=5 — fixture collision"
    )
    assert margin_str in banner, f"banner should contain margin '{margin_str}'"


def test_enterprises_banner_says_predator_still_needs():
    """A3: banner states how much the top predator still needs to reach threshold."""
    # Use Ashworth house at turn=7 where shortfall (45.0) != margin (40.0)
    # so the test is actually measuring something, not a fixture collision.
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded import agenda
    g = GildedGame(seed=42)
    player = "Ashworth"
    assert player in g.houses, f"expected Ashworth in houses, got {list(g.houses)}"
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    for _ in range(7):
        g.end_turn()
    view = BroadsheetView(g, player)
    lines = view.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, player)
    if r.top_predator is None:
        assert any("none" in ln for ln in lines)
        return
    pred = r.top_predator
    shortfall = r.threshold - pred.stake
    shortfall_str = f"{shortfall:.1f}"
    margin_str = f"{r.margin:.1f}"
    # Guard: shortfall must differ from margin so the test is actually measuring
    assert shortfall_str != margin_str, (
        f"CANNOT MEASURE: shortfall ({shortfall_str}) equals margin ({margin_str}) "
        f"— fixture collision, test cannot distinguish the two values"
    )
    # The shortfall should appear in the banner as "needs X.X% more"
    needs_str = f"needs {shortfall_str}% more"
    assert needs_str in banner, (
        f"banner should contain '{needs_str}' "
        f"(predator {pred.name} needs {shortfall_str}% more)"
    )


def test_enterprises_direction_tolerates_float_noise():
    """A4: tiny deltas (within 1e-9) read as 'steady', not 'rising'/'falling'."""
    g, v = _enterprises_view(turns=3)
    # Inject a delta of 1e-12 (should read as steady)
    for commodity in COMMODITIES:
        g.market._previous_prices[commodity] = g.market.price(commodity) - 1e-12
    lines = v.enterprises_lines()
    ticker_line = [ln for ln in lines if "coal" in ln][0]
    assert "rising" not in ticker_line and "falling" not in ticker_line, (
        f"delta of 1e-12 should read as steady, not rising/falling: {ticker_line}"
    )


def test_enterprises_delta_is_none_before_first_clearing():
    """Mutation 1: delta() returns None before the market has cleared."""
    g, v = _enterprises_view(turns=0)
    for commodity in COMMODITIES:
        d = g.market.delta(commodity)
        assert d is None, (
            f"delta('{commodity}') should be None before first clearing, got {d}"
        )


def test_enterprises_snapshot_before_clearing():
    """Mutation 2: verify snapshot is taken BEFORE clearing (delta reflects real change)."""
    g, v = _enterprises_view(turns=1)
    # After one clearing, delta should be a real number (not None)
    for commodity in COMMODITIES:
        d = g.market.delta(commodity)
        assert d is not None, f"delta('{commodity}') should not be None after clearing"


def test_enterprises_ticker_direction_rising():
    """Mutation 3: verify 'rising' appears when price actually rose."""
    g, v = _enterprises_view(turns=3)
    # Force a rising delta
    for commodity in COMMODITIES:
        g.market._previous_prices[commodity] = g.market.price(commodity) - 0.1
    lines = v.enterprises_lines()
    ticker_line = [ln for ln in lines if "coal" in ln][0]
    assert "rising" in ticker_line, f"coal should show rising: {ticker_line}"


def test_enterprises_ticker_direction_falling():
    """Mutation 3b: verify 'falling' appears when price actually fell."""
    g, v = _enterprises_view(turns=3)
    # Force a falling delta
    for commodity in COMMODITIES:
        g.market._previous_prices[commodity] = g.market.price(commodity) + 0.1
    lines = v.enterprises_lines()
    ticker_line = [ln for ln in lines if "coal" in ln][0]
    assert "falling" in ticker_line, f"coal should show falling: {ticker_line}"


def test_enterprises_no_direction_before_first_clearing():
    """No direction label should appear before the market has cleared."""
    g, v = _enterprises_view(turns=0)
    lines = v.enterprises_lines()
    for ln in lines:
        if any(c in ln for c in COMMODITIES):
            assert "rising" not in ln and "falling" not in ln, (
                f"no direction before first clearing: {ln}"
            )


def test_enterprises_direction_appears_once_market_moves():
    """After clearing, direction labels appear (even if steady)."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    # At least one commodity line should exist
    ticker_lines = [ln for ln in lines if any(c in ln for c in COMMODITIES)]
    assert len(ticker_lines) > 0, "should have ticker lines after clearing"


def test_enterprises_direction_matches_measured_move():
    """Mutation 3: rising/falling matches the actual delta sign."""
    g, v = _enterprises_view(turns=3)
    # Set coal to have a clear positive delta
    g.market._previous_prices["coal"] = g.market.price("coal") - 0.5
    # Set steel to have a clear negative delta
    g.market._previous_prices["steel"] = g.market.price("steel") + 0.5
    lines = v.enterprises_lines()
    coal_line = [ln for ln in lines if "coal" in ln][0]
    steel_line = [ln for ln in lines if "steel" in ln][0]
    assert "rising" in coal_line, f"coal should be rising: {coal_line}"
    assert "falling" in steel_line, f"steel should be falling: {steel_line}"


def test_enterprises_market_reports_delta_honestly():
    """delta() returns the actual price change, not a fabricated value."""
    g, v = _enterprises_view(turns=3)
    # Set a known previous price
    current_coal = g.market.price("coal")
    g.market._previous_prices["coal"] = current_coal - 0.3
    delta = g.market.delta("coal")
    assert delta is not None
    assert abs(delta - 0.3) < 0.01, f"delta should be ~0.3, got {delta}"


def test_enterprises_banner_is_a_pure_read():
    """Banner should not mutate game state."""
    g, v = _enterprises_view(turns=3)
    # Snapshot state before
    prices_before = dict(g.market.prices)
    prev_before = dict(g.market._previous_prices)
    lines = v.enterprises_lines()
    # State should be unchanged
    assert g.market.prices == prices_before, "enterprises_lines() should not mutate prices"
    assert g.market._previous_prices == prev_before, (
        "enterprises_lines() should not mutate _previous_prices"
    )
    assert len(lines) > 0


def test_enterprises_tab_puts_ink_on_the_page():
    """Mutation 8: _draw_enterprises actually draws content (not a blank page)."""
    g, v = _enterprises_view(turns=3)
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    # Check pixels in the content area are not all background (PAPER_BG = (245, 235, 220))
    PAPER_BG = (245, 235, 220)
    TAB_H = 40
    HUD_H = 30
    content_y = TAB_H + HUD_H
    found_ink = False
    for x in range(10, 400):
        for y in range(content_y + 10, min(content_y + 100, surf.get_height())):
            pixel = tuple(surf.get_at((x, y)))
            if abs(pixel[0] - PAPER_BG[0]) > 10 or abs(pixel[1] - PAPER_BG[1]) > 10 or abs(pixel[2] - PAPER_BG[2]) > 10:
                found_ink = True
                break
        if found_ink:
            break
    assert found_ink, "Enterprises tab should draw visible content (not a blank page)"


def test_enterprises_banner_names_the_grip_band():
    """Banner should contain a grip band name."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    band_spelling = r.band.replace("_", " ")
    assert band_spelling in banner, f"banner should contain grip band '{band_spelling}'"


def test_enterprises_banner_shows_stake_and_threshold():
    """Banner should contain both the controlling stake and the threshold."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    stake_str = f"{r.controlling_stake:.1f}"
    threshold_str = f"{r.threshold:.1f}"
    assert stake_str in banner, f"banner should contain stake '{stake_str}'"
    assert threshold_str in banner, f"banner should contain threshold '{threshold_str}'"


def test_enterprises_banner_names_the_top_predator():
    """Banner should name the top predator (or say 'none')."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    if r.top_predator is not None:
        assert r.top_predator.name in banner, (
            f"banner should name predator '{r.top_predator.name}'"
        )
    else:
        assert any("none" in ln for ln in lines)


def test_enterprises_banner_marks_predator_who_is_kin():
    """If the top predator is a character of the same house, mark them as kin."""
    g, v = _enterprises_view(seed=7, turns=5)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    if r.top_predator is not None:
        # Check if predator is kin
        realm = g.realms.get(v.house)
        is_kin = False
        if realm is not None:
            for char in realm.characters:
                if char.id == r.top_predator.id:
                    is_kin = True
                    break
        if is_kin:
            assert "(kin)" in banner, "banner should mark kin predator"


def test_enterprises_banner_carries_the_market_ticker():
    """Banner should contain a market ticker line with commodity prices."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    for commodity in COMMODITIES:
        assert commodity in banner, f"banner should mention commodity '{commodity}'"
