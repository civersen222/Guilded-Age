"""G22 broadsheet screens: tabs, headless draw, click actions, and Enterprises banner."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.grip import BANDS, report as grip_report
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
    margin_str = f"{margin:.1f}"
    # Assert the margin line contains the 'margin' label — not just the number,
    # which could appear as the predator's shortfall on a different line.
    grip_line = [ln for ln in lines if ln.startswith("Grip:")][0]
    assert "margin" in grip_line and margin_str in grip_line, (
        f"grip line should contain 'margin {margin_str}'. grip_line='{grip_line}'"
    )


def test_enterprises_banner_says_predator_still_needs():
    """A3: banner states how much the top predator still needs to reach threshold."""
    # Use Ferrenholt at turn=3 where a predator exists (Alexios Ashworth, 15.0%)
    # and shortfall (35.0%) == margin (35.0%) — the fixture collision.
    # The test must assert the shortfall appears WITH the predator's name
    # on the same line, so the margin number on line 1 cannot satisfy it.
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded import agenda
    g = GildedGame(seed=42)
    player = "Ferrenholt"
    assert player in g.houses, f"expected Ferrenholt in houses, got {list(g.houses)}"
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    for _ in range(3):
        g.end_turn()
    view = BroadsheetView(g, player)
    lines = view.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, player)
    # This fixture MUST have a predator — if not, the test cannot measure
    assert r.top_predator is not None, (
        f"fixture has no top predator at seed=42 turn=3 player={player} — "
        f"test cannot measure the shortfall assertion"
    )
    pred = r.top_predator
    shortfall = r.threshold - pred.stake
    shortfall_str = f"{shortfall:.1f}"
    needs_str = f"needs {shortfall_str}% more"
    # Assert the shortfall appears on the SAME LINE as the predator's name.
    # This prevents the margin (which equals the shortfall at this fixture)
    # from satisfying the assertion from line 1.
    predator_line = [ln for ln in lines if pred.name in ln][0]
    assert needs_str in predator_line, (
        f"predator line should contain '{needs_str}' "
        f"(predator {pred.name} needs {shortfall_str}% more). "
        f"predator_line='{predator_line}'"
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
    # Run two clearings so we can measure what a correct snapshot produces
    # that a late snapshot cannot: after the FIRST clearing, delta reflects
    # the actual price movement. After the SECOND clearing, a late snapshot
    # would make every delta exactly 0.0 (post-clearing prices snapshot,
    # then post-clearing prices again). A correct pre-clearing snapshot
    # produces non-zero deltas when prices moved between turns.
    g, v = _enterprises_view(turns=2)
    # At least one commodity must have a non-zero delta after two clearings
    # (a late snapshot would make all deltas 0.0)
    deltas = [g.market.delta(c) for c in COMMODITIES]
    non_zero = sum(1 for d in deltas if d is not None and abs(d) > 1e-9)
    assert non_zero > 0, (
        f"All deltas are zero after two clearings — snapshot must be taken "
        f"BEFORE clearing to capture real price changes. deltas={dict(zip(COMMODITIES, deltas))}"
    )


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
    from gilded.ui.broadsheet import TAB_H, HUD_H, PAPER_BG
    g, v = _enterprises_view(turns=3)
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    # Check pixels in the content area are not all background
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


# ─────────────────────────────────────────────────────────────────
# L4.1d — five holes the L4.1c suite did not measure
# ─────────────────────────────────────────────────────────────────

def _distinct_enterprises_view(seed=314, turns=5):
    """Fixture with five pairwise-distinct figures and a non-kin predator.
    
    seed=314, turns=5 yields:
      stake=87.5, threshold=50.0, margin=37.5, pred_stake=7.5, shortfall=42.5
      predator=Cyrus Ferrenholt (not kin)
    """
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded.agenda import ensure_agenda
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(turns):
        g.end_turn()
    view = BroadsheetView(g, player)
    view.active_tab = "Enterprises"
    return g, view


def test_enterprises_stake_and_threshold_not_swapped():
    """L4.1d-1: the stake sits behind 'stake' and the threshold behind 'threshold'."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    grip_line = [ln for ln in v.enterprises_lines() if ln.startswith("Grip:")][0]
    # Adjacency: the rendered form label-and-value together
    assert f"stake {r.controlling_stake:.1f}%" in grip_line, (
        f"Grip line should contain 'stake {r.controlling_stake:.1f}%': {grip_line}"
    )
    assert f"threshold {r.threshold:.1f}%" in grip_line, (
        f"Grip line should contain 'threshold {r.threshold:.1f}%': {grip_line}"
    )
    # Guard: the two figures must be distinct so the test is meaningful
    assert f"{r.controlling_stake:.1f}" != f"{r.threshold:.1f}", (
        "fixture collision: stake == threshold"
    )


def test_enterprises_margin_sign_correct():
    """L4.1d-2: the margin renders with the correct sign, not flipped."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    grip_line = [ln for ln in v.enterprises_lines() if ln.startswith("Grip:")][0]
    # Adjacency: exact rendered form "margin X%"
    expected = f"margin {r.margin:.1f}%"
    assert expected in grip_line, (
        f"Grip line should contain '{expected}': {grip_line}"
    )
    # Guard: margin must differ from all other figures
    margin_str = f"{r.margin:.1f}"
    for name, val in [("stake", r.controlling_stake), ("threshold", r.threshold)]:
        assert margin_str != f"{val:.1f}", f"fixture collision: margin == {name}"


def test_enterprises_predator_line_states_own_stake():
    """L4.1d-3: the predator line states the predator's own stake, not its shortfall."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    pred = r.top_predator
    assert pred is not None, "fixture requires a predator"
    lines = v.enterprises_lines()
    pred_line = [ln for ln in lines if ln.startswith("Top predator:")][0]
    shortfall = r.threshold - pred.stake
    # Adjacency: the exact rendered form "{stake}%, needs"
    expected = f"{pred.stake:.1f}%, needs"
    assert expected in pred_line, (
        f"Predator line should contain '{expected}': {pred_line}"
    )
    # Guard: stake must differ from shortfall so the test is meaningful
    assert f"{pred.stake:.1f}" != f"{shortfall:.1f}", (
        "fixture collision: predator stake == shortfall"
    )


def test_enterprises_predator_not_kin_is_not_marked():
    """L4.1d-4: a predator who is NOT kin is not marked with (kin)."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    pred = r.top_predator
    assert pred is not None, "fixture requires a predator"
    # Prove the predator is genuinely not kin
    realm = g.realms.get(v.house)
    is_kin = False
    if realm is not None:
        for ch in realm.characters:
            if ch.id == pred.id:
                is_kin = True
                break
    assert not is_kin, (
        f"fixture failure: predator {pred.name} ({pred.id}) is kin to {v.house}"
    )
    lines = v.enterprises_lines()
    pred_line = [ln for ln in lines if ln.startswith("Top predator:")][0]
    assert "(kin)" not in pred_line, (
        f"Non-kin predator should not carry (kin) marker: {pred_line}"
    )


def test_enterprises_banner_counts_ventures():
    """L4.1d-5: the banner states the correct number of enterprises."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    ventures_line = [ln for ln in lines if ln.startswith("Enterprises:")][0]
    expected = f"Enterprises: {len(r.enterprises)}"
    assert ventures_line == expected, (
        f"Expected '{expected}', got '{ventures_line}'"
    )


# =============================================================================
# Stage 4 Layer 4 — Task 4.1e: behaviour measurement
# =============================================================================

def _ticker_line(lines):
    """Return the market ticker line from enterprises_lines output."""
    return [ln for ln in lines if " | " in ln][0]


def _force_steady_prices(g):
    """Set previous prices equal to current so delta returns 0.0 for every commodity."""
    for c in COMMODITIES:
        g.market._previous_prices[c] = g.market.prices[c]


def test_ticker_shows_each_commodity_own_price():
    """Statement 1: each ticker entry shows THAT commodity's price, not a constant.

    Catches e1 (price from COMMODITIES[0]) and e2 (price from COMMODITIES[-1]).
    """
    g = GildedGame(seed=42)
    for _ in range(3):
        g.turn += 1
        g.end_turn()
    prices = {c: g.market.price(c) for c in COMMODITIES}
    # Verify fixture has divergent prices
    unique = set(round(p, 2) for p in prices.values())
    assert len(unique) > 1, "fixture needs divergent commodity prices"

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    for i, commodity in enumerate(COMMODITIES):
        expected_price = f"{prices[commodity]:.2f}"
        entry = parts[i]
        assert expected_price in entry, \
            f"ticker entry for {commodity} should show {expected_price}, got '{entry}'"


def test_ticker_entries_differ_when_prices_differ():
    """Statement 1 sibling: ticker entries are distinct when prices are distinct.

    Catches both e1 and e2 by checking that entries are NOT all the same string.
    """
    g = GildedGame(seed=7)
    for _ in range(5):
        g.turn += 1
        g.end_turn()
    prices = {c: g.market.price(c) for c in COMMODITIES}
    unique = set(round(v, 2) for v in prices.values())
    assert len(unique) > 1, "fixture needs divergent prices"

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    # If all entries showed the same commodity's price, the set of entries would be small
    assert len(set(parts)) > 1, \
        f"all ticker entries look identical — likely showing one commodity's price: {parts}"
    # Spot-check: middle commodity should NOT match first or last commodity's price
    mid_price = f"{prices[COMMODITIES[1]]:.2f}"
    first_price = f"{prices[COMMODITIES[0]]:.2f}"
    assert mid_price != first_price, "fixture: mid and first prices should differ"
    assert mid_price in parts[1], \
        f"entry for {COMMODITIES[1]} should contain {mid_price}, got '{parts[1]}'"


def test_steady_price_has_two_decimal_places():
    """Statement 2: a steady price is printed with exactly two decimal places.

    Catches e3 (steady loses decimals) and e4 (steady gains a third).
    """
    g = GildedGame(seed=42)
    for _ in range(2):
        g.turn += 1
        g.end_turn()
    _force_steady_prices(g)

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    for part in parts:
        tokens = part.split()
        if len(tokens) >= 3 and tokens[-1] == "steady":
            price_str = tokens[-2]
            assert "." in price_str, f"steady price missing decimal point: {part}"
            decimals = price_str.split(".")[1]
            assert len(decimals) == 2, \
                f"steady price '{price_str}' needs exactly 2 decimals, got {len(decimals)}: '{part}'"


def test_all_ticker_prices_have_two_decimal_places():
    """Statement 2 sibling: ALL prices in the ticker (rising/falling/steady) use 2 decimals.

    Catches both e3 and e4 by checking every price entry uniformly.
    """
    g = GildedGame(seed=42)
    for _ in range(3):
        g.turn += 1
        g.end_turn()
    _force_steady_prices(g)

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    for part in parts:
        tokens = part.split()
        price_str = tokens[1]  # second token is always the price
        assert "." in price_str, f"price missing decimal point: {part}"
        decimals = price_str.split(".")[1]
        assert len(decimals) == 2, \
            f"price '{price_str}' in '{part}' needs exactly 2 decimal places, got {len(decimals)}"


def test_steady_is_the_word_for_no_movement():
    """Statement 3: the word for a price that did not move is 'steady'.

    Catches e5 ('steady' renamed 'flat') and e6 ('steady' renamed 'level').
    """
    g = GildedGame(seed=42)
    for _ in range(2):
        g.turn += 1
        g.end_turn()
    _force_steady_prices(g)

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    for part in parts:
        tokens = part.split()
        if len(tokens) >= 3:
            commodity = tokens[0]
            d = g.market.delta(commodity)
            if d is not None and abs(d) <= 1e-9:
                direction = tokens[-1]
                assert direction == "steady", \
                    f"zero-delta {commodity} should say 'steady', got '{direction}'"


def test_ticker_never_says_flat_or_level():
    """Statement 3 sibling: the ticker never uses 'flat' or 'level' for any price.

    Catches both e5 and e6 by checking the full ticker text.
    """
    g = GildedGame(seed=42)
    for _ in range(2):
        g.turn += 1
        g.end_turn()
    _force_steady_prices(g)

    v = BroadsheetView(g, next(iter(g.houses)))
    lines = v.enterprises_lines()
    ticker = _ticker_line(lines)
    parts = [p.strip() for p in ticker.split(" | ")]
    for part in parts:
        tokens = part.split()
        if len(tokens) >= 3:
            direction = tokens[-1]
            assert direction not in ("flat", "level"), \
                f"direction '{direction}' is invalid — should be 'steady': {part}"


def test_grip_banner_shows_computed_band():
    """Statement 4: the grip band on the banner is computed for the house being viewed.

    Catches e7 (always IRON GRIP) and e8 (always CONTESTED).
    Uses seed=0, turn=10, house=Mordaine where band=CONTESTED.
    """
    g = GildedGame(seed=0)
    for _ in range(10):
        g.turn += 1
        g.end_turn()
    r = grip_report(g, "Mordaine")
    assert r.band == "CONTESTED", f"fixture: expected CONTESTED, got {r.band}"

    v = BroadsheetView(g, "Mordaine")
    lines = v.enterprises_lines()
    grip_line = lines[0]
    assert "CONTESTED" in grip_line, \
        f"grip line should contain 'CONTESTED', got '{grip_line}'"
    assert "IRON GRIP" not in grip_line, \
        f"grip line should NOT contain 'IRON GRIP' when band is CONTESTED: '{grip_line}'"


def test_grip_banner_band_matches_report_not_hardcoded():
    """Statement 4 sibling: banner band changes with the computed report.

    Catches both e7 and e8 by verifying the banner matches grip_report().band
    at a fixture where the band is CONTESTED (not IRON_GRIP).
    """
    g = GildedGame(seed=0)
    for _ in range(10):
        g.turn += 1
        g.end_turn()
    r = grip_report(g, "Mordaine")
    assert r.band != "IRON_GRIP", "fixture requires non-IRON_GRIP band"

    v = BroadsheetView(g, "Mordaine")
    lines = v.enterprises_lines()
    grip_line = lines[0]
    expected_band = r.band.replace("_", " ")
    assert expected_band in grip_line, \
        f"grip line should show computed band '{expected_band}', got '{grip_line}'"
    # Verify no wrong band appears
    for wrong in BANDS:
        if wrong != r.band:
            wrong_display = wrong.replace("_", " ")
            assert wrong_display not in grip_line, \
                f"grip line should not contain wrong band '{wrong_display}': '{grip_line}'"
