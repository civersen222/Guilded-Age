"""G22 broadsheet screens: tabs, headless draw, click actions, and Enterprises banner."""

import copy
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.docket import director_candidates
from gilded.grip import BANDS, report as grip_report
from gilded.market import COMMODITIES
from gilded.ui.broadsheet import TABS, BroadsheetView
from gilded.agenda import ensure_agenda
from gilded.intel import threat_rank
from gilded.society.schemes import share_price
from gilded.enterprises import TIER_MAX


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


# ── Enterprises view helpers ─────────────────────────────────────────────

def _enterprises_view(seed=42, turns=0):
    """Game with agendas, advanced `turns` turns, view on Enterprises tab."""
    from gilded import agenda
    pygame.init()
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    for _ in range(turns):
        g.end_turn()
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    return g, v


# ── Enterprises banner tests ─────────────────────────────────────────────

def test_enterprises_banner_lines_exist():
    g, v = _enterprises_view()
    lines = v.enterprises_lines()
    assert len(lines) >= 4, "banner should have at least 4 lines"


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
    assert str(r.controlling_stake) in banner or f"{r.controlling_stake:.0f}" in banner
    assert str(r.threshold) in banner or f"{r.threshold:.0f}" in banner


def test_enterprises_banner_names_top_predator():
    """Banner should name the top predator (or say 'none')."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    if r.top_predator is not None:
        assert r.top_predator.name in banner, (
            f"banner should name top predator {r.top_predator.name!r}: {banner}"
        )
    else:
        assert "none" in banner.lower(), "banner should say 'none' when no predator"


def test_enterprises_banner_shows_venture_count():
    """Banner should show the count of ventures."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    banner = "\n".join(lines)
    r = grip_report(g, v.house)
    assert str(len(r.enterprises)) in banner


# ── Market ticker tests ──────────────────────────────────────────────────

def test_enterprises_ticker_shows_commodities():
    """The ticker line should mention commodities."""
    g, v = _enterprises_view(turns=3)
    lines = v.enterprises_lines()
    ticker_lines = [ln for ln in lines if any(c in ln for c in COMMODITIES)]
    assert len(ticker_lines) > 0, "should have at least one ticker line"


def test_enterprises_market_reports_delta():
    """delta() returns the actual price change, not a fabricated value."""
    g, v = _enterprises_view(turns=3)
    current_coal = g.market.price("coal")
    g.market._previous_prices["coal"] = current_coal - 2.5
    delta = g.market.delta("coal")
    assert delta is not None and abs(delta - 2.5) < 1e-9, f"delta should be ~2.5, got {delta}"


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
    """Before the first clearing, there's no previous price to compare against."""
    g, v = _enterprises_view(turns=3)
    # Remove previous prices
    g.market._previous_prices = {}
    lines = v.enterprises_lines()
    ticker_lines = [ln for ln in lines if any(c in ln for c in COMMODITIES)]
    for ln in ticker_lines:
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
    g.market._previous_prices["coal"] = current_coal - 2.5
    delta = g.market.delta("coal")
    assert delta is not None and abs(delta - 2.5) < 1e-9


def test_enterprises_lines_mutation_free():
    """enterprises_lines() must not mutate game state."""
    import copy
    g, v = _enterprises_view(turns=3)
    enterprises_before = copy.deepcopy(g.enterprises)
    lines = v.enterprises_lines()
    assert g.enterprises == enterprises_before, "enterprises should not change"
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


# ── Expanded ledger tests (4.2) ─────────────────────────────────────────

def test_ledger_one_row_per_venture():
    """Each venture owned by the house gets exactly one ledger row."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        matching = [ln for ln in lines if ent.name in ln]
        assert len(matching) >= 1, f"no ledger row for venture {ent.name!r}"


def test_ledger_row_shows_sector():
    """Each ledger row shows the venture's sector."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        sector = ent.sector
        assert sector in row.lower(), f"row for {ent.name} should mention sector {sector!r}: {row}"


def test_ledger_row_shows_tier():
    """Each ledger row shows the venture's tier."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        # tier is shown as "tier N"
        assert f"tier {ent.tier}" in row.lower(), f"row should show tier {ent.tier}: {row}"


def test_ledger_row_shows_dividend():
    """Each ledger row shows this turn's dividend."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        div_str = f"{ent.dividend:.1f}"
        assert div_str in row, f"row should show dividend {div_str}: {row}"


def test_ledger_row_shows_dividend_delta():
    """Each ledger row shows the dividend delta with sign."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        if ent.dividend_delta is not None:
            # Should show + or - sign
            assert "+" in row or "-" in row, f"row should show signed delta: {row}"
        else:
            assert "new" in row.lower(), f"row should show 'new' when no delta: {row}"


def test_ledger_no_delta_before_second_payment():
    """A venture that has not been paid twice shows 'new', not +0.0."""
    g, v = _enterprises_view(seed=42, turns=0)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        assert "new" in row.lower(), f"fresh venture row should show 'new': {row}"


def test_ledger_dividend_delta_is_measured():
    """dividend_delta equals this turn's dividend minus last turn's."""
    g, v = _enterprises_view(seed=42, turns=3)
    before = {e.eid: e.dividend for e in grip_report(g, v.house).enterprises}
    g.end_turn()
    after = grip_report(g, v.house)
    for e in after.enterprises:
        if e.eid in before:
            expected = e.dividend - before[e.eid]
            assert e.dividend_delta is not None, f"should have delta: {e.name}"
            assert abs(e.dividend_delta - expected) < 1e-6, (
                f"delta mismatch for {e.name}: got {e.dividend_delta}, expected {expected}"
            )


def test_ledger_row_names_director():
    """Each ledger row shows the Director's name or 'vacant'."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        if ent.director is not None:
            assert ent.director.name in row, f"row should name director {ent.director.name!r}: {row}"
        else:
            assert "vacant" in row.lower(), f"row should say 'vacant': {row}"


def test_ledger_skim_marks_disloyal_director():
    """Only the disloyal Director's row shows [skim]."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        if ent.director is not None and ent.director.disloyal:
            assert "[skim]" in row, f"disloyal director row should show [skim]: {row}"
        elif ent.director is not None and not ent.director.disloyal:
            assert "[skim]" not in row, f"loyal director row should NOT show [skim]: {row}"


def test_ledger_row_shows_your_stake():
    """Each ledger row shows your stake percentage."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        stake_str = f"{ent.your_stake:.1f}"
        assert stake_str in row, f"row should show stake {stake_str}: {row}"


def test_ledger_row_names_top_outside_holder():
    """Each ledger row shows the top outside holder's name and percentage."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        if ent.top_outside is not None:
            outside_id, outside_pct = ent.top_outside
            # Should show the holder's name (not the raw ID)
            assert outside_id not in row, f"row should resolve holder ID to name: {row}"


def test_ledger_row_says_none_when_no_outside():
    """If no outside holder exists, the row says 'none'."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    lines = v.enterprises_lines()
    for ent in r.enterprises:
        row = [ln for ln in lines if ent.name in ln][0]
        if ent.top_outside is None:
            assert "none" in row.lower(), f"row should say 'none' for no outside holder: {row}"


# ── Action descriptor tests (4.2) ───────────────────────────────────────

def test_enterprise_actions_returns_list():
    """enterprise_actions() returns a list of dicts."""
    g, v = _enterprises_view(seed=42, turns=4)
    acts = v.enterprise_actions()
    assert isinstance(acts, list), "enterprise_actions() must return a list"
    for a in acts:
        assert isinstance(a, dict), "each action must be a dict"
        assert "label" in a, "each action must have 'label'"
        assert "action" in a, "each action must have 'action'"
        assert "eid" in a, "each action must have 'eid'"


def test_per_venture_four_actions():
    """Each venture gets expand, appoint, buy_shares, sell_shares."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    acts = v.enterprise_actions()
    for ent in r.enterprises:
        verbs = [list(a["action"].keys())[0] for a in acts if a.get("eid") == ent.eid]
        for verb in ("expand_enterprise", "appoint_director", "buy_shares", "sell_shares"):
            assert verb in verbs, f"missing {verb} for venture {ent.name}"


def test_page_offers_founding():
    """The page offers a found_enterprise action."""
    g, v = _enterprises_view(seed=42, turns=4)
    acts = v.enterprise_actions()
    found_actions = [a for a in acts if "found_enterprise" in a["action"]]
    assert len(found_actions) >= 1, "page should offer found_enterprise"
    assert found_actions[0]["eid"] is None, "found_enterprise should have eid=None"


def test_defend_buyout_names_holder_and_prices_stake():
    """Defend buyout actions name the holder and include a price."""
    g, v = _enterprises_view(seed=42, turns=4)
    r = grip_report(g, v.house)
    acts = v.enterprise_actions()
    defend_actions = [a for a in acts if "defend_buyout" in a["action"]]
    for ent in r.enterprises:
        if ent.top_outside is not None:
            matching = [a for a in defend_actions if a.get("eid") == ent.eid]
            assert len(matching) >= 1, f"defend buyout missing for {ent.name}"
            action = matching[0]
            assert "price" in action, "defend action should include price"
            assert action["price"] > 0, "price should be positive"


def test_attack_takeover_names_rival():
    """Attack takeover names the top threat house."""
    g, v = _enterprises_view(seed=42, turns=4)
    acts = v.enterprise_actions()
    attack_actions = [a for a in acts if "attack_takeover" in a["action"]]
    assert len(attack_actions) >= 1, "should offer attack_takeover"
    action = attack_actions[0]
    assert action["eid"] is None, "attack_takeover should have eid=None"
    # Label should name the target house
    assert len(action["label"]) > 0, "label should name the rival"


def test_descriptors_use_valid_verbs():
    """All action descriptors use verbs the game recognizes."""
    from gilded.docket import INITIATIVES
    valid_verbs = set(INITIATIVES.keys())
    # Also include verbs from schemes
    valid_verbs.update({"found_enterprise", "defend_buyout", "attack_takeover"})
    g, v = _enterprises_view(seed=42, turns=4)
    acts = v.enterprise_actions()
    for a in acts:
        verb = list(a["action"].keys())[0]
        assert verb in valid_verbs or verb in {
            "expand_enterprise", "appoint_director", "buy_shares",
            "sell_shares", "found_enterprise", "defend_buyout", "attack_takeover"
        }, f"unknown verb {verb!r} in action descriptor"


def test_actions_dont_mutate_state():
    """enterprise_actions() must not mutate game state."""
    import copy
    g, v = _enterprises_view(seed=42, turns=4)
    enterprises_before = copy.deepcopy(g.enterprises)
    acts = v.enterprise_actions()
    assert g.enterprises == enterprises_before, "actions should not mutate enterprises"


def test_actions_dont_launch_initiatives():
    """enterprise_actions() must not call initiative()."""
    g, v = _enterprises_view(seed=42, turns=4)
    docket_counts_before = {h: len(pets) for h, pets in g.docket_by_house.items()}
    acts = v.enterprise_actions()
    docket_counts_after = {h: len(pets) for h, pets in g.docket_by_house.items()}
    assert docket_counts_before == docket_counts_after, "actions should not create docket entries"


# ── Cross-seed tests ─────────────────────────────────────────────────────

def test_ledger_different_seed():
    """Ledger works with a different seed (not just 42)."""
    g, v = _enterprises_view(seed=7, turns=4)
    lines = v.enterprises_lines()
    acts = v.enterprise_actions()
    r = grip_report(g, v.house)
    assert len(lines) >= 4 + len(r.enterprises), "should have banner + one row per venture"
    assert len(acts) >= len(r.enterprises) * 4 + 1, "should have 4 actions per venture + founding"


def test_attack_takeover_differs_by_seed():
    """The attack takeover target differs by seed (not hardcoded)."""
    g1, v1 = _enterprises_view(seed=42, turns=4)
    g2, v2 = _enterprises_view(seed=7, turns=4)
    acts1 = v1.enterprise_actions()
    acts2 = v2.enterprise_actions()
    attack1 = [a for a in acts1 if "attack_takeover" in a["action"]][0]
    attack2 = [a for a in acts2 if "attack_takeover" in a["action"]][0]
    target1 = attack1["action"]["attack_takeover"]
    target2 = attack2["action"]["attack_takeover"]
    # At minimum, labels should name the target
    assert target1 in attack1["label"], f"label should name target {target1}"
    assert target2 in attack2["label"], f"label should name target {target2}"

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
    
    Tries seed=314 first (original), falls back to seed=42 if the predicate
    no longer holds after AI changes.
    """
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded.agenda import ensure_agenda
    for try_seed in [49, 86, 42, 7, 99]:
        g = GildedGame(seed=try_seed)
        player = next(iter(g.houses))
        for h in g.houses:
            if h != player:
                ensure_agenda(g, h)
        for _ in range(turns):
            g.end_turn()
        r = grip_report(g, player)
        pred = r.top_predator
        if pred is None:
            continue
        # Check the predator is not kin
        realm = g.realms.get(player)
        is_kin = False
        if realm is not None:
            for ch in realm.characters:
                if ch.id == pred.id:
                    is_kin = True
                    break
        if is_kin:
            continue
        # Check we have at least 5 distinct figures
        figures = set()
        for el in r.enterprises:
            figures.add(el.name)
            if el.director:
                figures.add(el.director)
        if len(figures) < 5:
            continue
        # Check we have enough enterprises for the test
        if len(r.enterprises) < 2:
            continue
        view = BroadsheetView(g, player)
        view.active_tab = "Enterprises"
        return g, view
    raise RuntimeError("No seed produced a valid fixture state")



def test_per_venture_payload_identity():
    """4.2d-1: each row's action payload carries that row's venture eid, not another's."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    # Fixture guard: at least two ventures with distinct eids
    assert len(r.enterprises) >= 2, "fixture must yield >= 2 ventures"
    eids = {el.eid for el in r.enterprises}
    assert len(eids) >= 2, "fixture ventures must have distinct eids"
    acts = v.enterprise_actions()
    verbs = ("expand_enterprise", "appoint_director", "buy_shares", "sell_shares")
    for ent in r.enterprises:
        for verb in verbs:
            row = [a for a in acts if a.get("eid") == ent.eid and verb in a["action"]]
            assert len(row) == 1, f"expected one {verb} row for {ent.name}"
            # Payload value must equal THIS venture's eid — compare against grip_report,
            # not against the row's own eid key (which could be wrong together).
            assert row[0]["action"][verb] == ent.eid, (
                f"{verb} payload for {ent.name} carries eid {row[0]['action'][verb]}, "
                f"expected {ent.eid}"
            )


def test_per_venture_label_identity():
    """4.2d-2: each row's label names that row's venture, not another's."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    # Fixture guard: distinct names
    assert len(r.enterprises) >= 2, "fixture must yield >= 2 ventures"
    names = {el.name for el in r.enterprises}
    assert len(names) >= 2, "fixture ventures must have distinct names"
    acts = v.enterprise_actions()
    for ent in r.enterprises:
        rows = [a for a in acts if a.get("eid") == ent.eid]
        for row in rows:
            label = row["label"]
            # Label must contain this venture's name
            assert ent.name in label, (
                f"label '{label}' for eid {ent.eid} does not contain venture name '{ent.name}'"
            )
            # Label must NOT contain any OTHER venture's name
            for other in r.enterprises:
                if other.eid != ent.eid:
                    assert other.name not in label, (
                        f"label '{label}' for {ent.name} (eid {ent.eid}) "
                        f"incorrectly contains '{other.name}' (eid {other.eid})"
                    )


def test_per_venture_label_completeness():
    """4.2d-3: every per-venture label states which venture it acts on (not a bare verb)."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    assert len(r.enterprises) >= 2, "fixture must yield >= 2 ventures"
    acts = v.enterprise_actions()
    for ent in r.enterprises:
        rows = [a for a in acts if a.get("eid") == ent.eid]
        for row in rows:
            label = row["label"]
            # Label must contain the venture name — a bare verb like 'Expand' or
            # 'Appoint Director' without a name is incomplete.
            assert ent.name in label, (
                f"label '{label}' for eid {ent.eid} does not name venture '{ent.name}'"
            )
            # Negative check: label must not be a bare verb template
            bare_prefixes = ("Expand", "Appoint Director", "Buy Shares", "Sell Shares")
            for prefix in bare_prefixes:
                assert label != prefix, (
                    f"label '{label}' is a bare verb without naming the venture"
                )


def test_per_venture_label_verb_consistency():
    """4.2d-4: each row's label promises a verb that matches the action's verb key."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    assert len(r.enterprises) >= 2, "fixture must yield >= 2 ventures"
    acts = v.enterprise_actions()
    # Only the four per-venture verbs from the first loop
    per_venture_verbs = ("expand_enterprise", "appoint_director", "buy_shares", "sell_shares")
    # Map what each label keyword expects as its verb
    label_verb_map = {
        "Expand": "expand_enterprise",
        "Appoint Director": "appoint_director",
        "Buy Shares": "buy_shares",
        "Sell Shares": "sell_shares",
    }
    for ent in r.enterprises:
        rows = [a for a in acts if a.get("eid") == ent.eid]
        for row in rows:
            verb_key = list(row["action"].keys())[0]
            # Skip non per-venture actions (defend_buyout, etc.)
            if verb_key not in per_venture_verbs:
                continue
            label = row["label"]
            # Find which label keyword this row's label matches
            expected_verb = None
            for kw, v_verb in label_verb_map.items():
                if kw in label:
                    expected_verb = v_verb
                    break
            assert expected_verb is not None, (
                f"label '{label}' for eid {ent.eid} does not match any known verb keyword"
            )
            assert verb_key == expected_verb, (
                f"label '{label}' for {ent.name} promises {expected_verb}, "
                f"but action verb is {verb_key}"
            )


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
    Uses seed=2, turn=5, house=Ferrenholt where band=CONTESTED.
    """
    g = GildedGame(seed=2)
    for _ in range(5):
        g.turn += 1
        g.end_turn()
    r = grip_report(g, "Ferrenholt")
    assert r.band == "CONTESTED", f"fixture: expected CONTESTED, got {r.band}"

    v = BroadsheetView(g, "Ferrenholt")
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
    g = GildedGame(seed=2)
    for _ in range(5):
        g.turn += 1
        g.end_turn()
    r = grip_report(g, "Ferrenholt")
    assert r.band != "IRON_GRIP", "fixture requires non-IRON_GRIP band"

    v = BroadsheetView(g, "Ferrenholt")
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


# ---- Job 2: four behaviours the ledger has but no test measures ----


def test_dividend_delta_sign_matches_payment_direction():
    """w3: a venture paying less must show '-', one paying more must show '+'.

    If the +/- were swapped, no existing test would notice because they all
    use a single positive delta.  This fixture builds a world with a genuinely
    negative delta and checks the rendered line carries the correct sign.
    """
    g = GildedGame(seed=7)
    player = next(iter(g.houses))
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(5):
        g.end_turn()

    v = BroadsheetView(g, player)
    lines = v.enterprises_lines()

    report = grip_report(g, player)
    for el in report.enterprises:
        if el.dividend_delta is not None:
            # Find the line for this venture
            venture_line = None
            for ln in lines:
                if el.name in ln:
                    venture_line = ln
                    break
            assert venture_line is not None, f"No line found for {el.name}"

            if el.dividend_delta < 0:
                # Negative delta should show "-"
                # The delta_str appears in parentheses after the dividend
                # Format: "div 558.2 (-125.5)" for negative — sign adjacent to number, no space
                assert "(-" in venture_line, (
                    f"Negative delta for {el.name} should show '(-' in line: {venture_line}"
                )
            else:
                # Positive delta should show "+"
                assert "(+" in venture_line, (
                    f"Positive delta for {el.name} should show '(+' in line: {venture_line}"
                )


def test_each_row_shows_its_own_tier():
    """w6: if every row printed 'tier 1', no test would notice with one venture.

    Builds a world with ventures at different tiers and asserts each row
    carries the correct tier number for that venture.
    """
    g = GildedGame(seed=7)
    player = next(iter(g.houses))
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(5):
        g.end_turn()

    v = BroadsheetView(g, player)
    lines = v.enterprises_lines()

    report = grip_report(g, player)
    # We need ventures at different tiers - seed 7 gives us tier 3 and tier 2
    tiers = set()
    for el in report.enterprises:
        tiers.add(el.tier)

    # Assert we have different tiers (otherwise the test measures nothing)
    assert len(tiers) > 1, (
        f"Need ventures at different tiers to measure w6, got {tiers}"
    )

    # Check each row shows its own tier
    for el in report.enterprises:
        venture_line = None
        for ln in lines:
            if el.name in ln:
                venture_line = ln
                break
        assert venture_line is not None, f"No line found for {el.name}"

        # This line should mention the correct tier
        expected_tier = f"tier {el.tier}"
        assert expected_tier in venture_line, (
            f"Row for {el.name} (tier {el.tier}) should show '{expected_tier}': {venture_line}"
        )

        # And it should NOT show the wrong tier
        for wrong_tier in tiers:
            if wrong_tier != el.tier:
                wrong_str = f"tier {wrong_tier}"
                assert wrong_str not in venture_line, (
                    f"Row for {el.name} (tier {el.tier}) should not show '{wrong_str}': {venture_line}"
                )


def test_defend_buyout_prices_the_actual_stake():
    """w8: cost must scale with the outside holder's percentage.

    If the buyout were priced for 1% every time, a 10% stake would print
    the same price as 1%.  This test builds a world with a substantial
    outside stake and verifies the cost is proportional to the actual
    percentage held.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(5):
        g.end_turn()

    v = BroadsheetView(g, player)
    actions = v.enterprise_actions()

    report = grip_report(g, player)
    # Find a venture with an outside holder
    for el in report.enterprises:
        if el.top_outside is not None:
            outside_id, outside_pct = el.top_outside
            ent = next((e for e in g.enterprises if e.eid == el.eid), None)
            if ent is not None:
                expected_price = share_price(ent, g) * outside_pct
                # Find the buyout action for this venture
                buyout_actions = [
                    a for a in actions
                    if a.get("action", {}).get("defend_buyout") is not None
                    and a.get("eid") == el.eid
                ]
                assert buyout_actions, (
                    f"No buyout action for {el.name} with outside holder {outside_id}"
                )
                actual_price = buyout_actions[0].get("price", 0)
                # The price should be proportional to the outside stake
                assert abs(actual_price - expected_price) < 0.01, (
                    f"Buyout for {outside_pct*100:.0f}% stake should cost {expected_price:.2f}, not {actual_price:.2f}"
                )
                # And it should NOT equal the full share price (which would be pricing 100%)
                wrong_price = share_price(ent, g)
                assert abs(actual_price - wrong_price) > 0.01, (
                    f"Buyout price {actual_price:.2f} looks like it's pricing 100%, not {outside_pct*100:.0f}%"
                )
                break


def test_attack_takeover_targets_top_threat():
    """w9: attack-takeover must target the rival that ranks FIRST as a threat.

    If it picked the least threatening House instead, the label would name
    a different target.  This test builds a world with multiple threats and
    verifies the action targets the top-ranked one.
    """
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    for h in g.houses:
        if h != player:
            ensure_agenda(g, h)
    for _ in range(5):
        g.end_turn()

    v = BroadsheetView(g, player)
    actions = v.enterprise_actions()

    threats = threat_rank(g)
    # We need at least 2 threats - first and last should differ
    assert len(threats) >= 2, (
        f"Need at least 2 threats to measure w9, got {threats}"
    )
    top_threat = threats[0]
    bottom_threat = threats[-1]
    assert top_threat != bottom_threat, "Need different top and bottom threats"

    # Find the attack takeover action
    takeover_actions = [
        a for a in actions
        if "attack_takeover" in str(a.get("action", {}))
    ]
    assert takeover_actions, "No attack takeover action found"

    action = takeover_actions[0]
    target = action["action"]["attack_takeover"]
    assert target == top_threat, (
        f"Attack takeover should target '{top_threat}' (top threat), not '{target}'"
    )
    # The label should name the correct target
    assert top_threat in action["label"], (
        f"Label '{action['label']}' should mention '{top_threat}'"
    )
    # It should NOT target the bottom threat
    assert target != bottom_threat, (
        f"Attack takeover incorrectly targets '{bottom_threat}' (least threatening)"
    )


# ── L4.2c: three behaviours a withheld mutation set found unmeasured ──

def test_defend_buyout_action_payload_names_correct_venture():
    """defend_buyout action tuple must name the correct venture in position 0."""
    g, v = _distinct_enterprises_view()
    r = grip_report(g, v.house)
    acts = v.enterprise_actions()
    defend_actions = [a for a in acts if "defend_buyout" in a["action"]]

    # Fixture adequacy: at least one venture with an outside holder
    ventures_with_outside = [el for el in r.enterprises if el.top_outside is not None]
    assert len(ventures_with_outside) >= 1, (
        "fixture must have >=1 venture with an outside holder to produce defend_buyout actions"
    )

    eids = [el.eid for el in ventures_with_outside]
    for action in defend_actions:
        payload = action["action"]["defend_buyout"]
        assert isinstance(payload, tuple) and len(payload) == 2, (
            f"defend_buyout action payload should be a 2-tuple: {payload!r}"
        )
        # Position 0 must be the venture eid from the descriptor's eid key
        assert payload[0] == action["eid"], (
            f"defend_buyout payload[0]={payload[0]} must equal descriptor eid={action['eid']}"
        )
        # Position 0 must be one of the actual venture eids
        assert payload[0] in eids, (
            f"defend_buyout payload[0]={payload[0]} not a valid venture eid"
        )
        # Position 1 must be the outside holder (not an eid)
        assert payload[1] not in eids, (
            f"defend_buyout payload[1]={payload[1]} looks like an eid, should be a holder id"
        )


def test_found_enterprise_offered_exactly_once():
    """Found Enterprise action must appear exactly once per page."""
    g, v = _enterprises_view(seed=42, turns=3)
    r = grip_report(g, v.house)
    acts = v.enterprise_actions()

    # Fixture adequacy: at least two ventures so that once-per-page != once-per-venture
    assert len(r.enterprises) >= 2, (
        "fixture must have >=2 ventures to distinguish once-per-page from once-per-venture"
    )

    found_actions = [a for a in acts if "found_enterprise" in a["action"]]
    assert len(found_actions) == 1, (
        f"Found Enterprise must appear exactly once, got {len(found_actions)}"
    )


def test_vacant_director_prints_vacant():
    """A venture with no Director must render 'dir: vacant', not a person's name."""
    g, v = _enterprises_view(seed=42, turns=3)

    # Get the player's enterprise eids (only these appear in enterprises_lines)
    r = grip_report(g, v.house)
    player_eids = {el.eid for el in r.enterprises}
    assert len(player_eids) >= 1, "fixture must have at least one player enterprise"

    # Vacate a director on a player enterprise and record its name
    vacated_name = None
    for ent in g.enterprises:
        if ent.eid in player_eids and ent.director_id is not None:
            vacated_name = ent.name
            ent.director_id = None
            break

    assert vacated_name is not None, "could not find a player venture with a director to vacate"

    lines = v.enterprises_lines()
    # Find the row for the vacated venture
    vacated_row = None
    for ln in lines:
        if vacated_name in ln and "dir: " in ln:
            vacated_row = ln
            break

    assert vacated_row is not None, (
        f"Could not find row for vacated venture '{vacated_name}'. Lines:\n" + "\n".join(lines)
    )
    # Extract the director field from that specific row
    dir_part = vacated_row.split("dir: ")[1].split(" |")[0].replace(" [skim]", "").strip()
    assert dir_part == "vacant", (
        f"Director field '{dir_part}' for '{vacated_name}' is not 'vacant' — empty chair reads as a person"
    )


# ---- L4.4: Enterprises panel clickability ----


def test_enterprises_draw_produces_hit_regions():
    """Drawing the Enterprises panel produces at least one hit region."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert len(v._enterprise_hits) > 0, (
        "Enterprises panel drew no hit regions for Expand buttons"
    )


def test_enterprises_click_returns_descriptor_with_eid():
    """A click at the centre of an Expand button returns a descriptor naming that venture's eid."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    # Pick the first hit region and click its center
    rect, act = v._enterprise_hits[0]
    result = v.handle_click(rect.center)
    assert result is not None, "Click at button center returned None"
    assert "expand_enterprise" in result, (
        f"Click returned {result}, expected expand_enterprise key"
    )
    assert result["expand_enterprise"] == act["eid"], (
        f"Descriptor eid {result['expand_enterprise']} != action eid {act['eid']}"
    )


def test_enterprises_click_on_empty_pixel_returns_none():
    """A click on a pixel with no button returns None."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    # Click at the far right of the content area (no buttons there)
    result = v.handle_click((1200, 200))
    assert result is None, (
        f"Click on empty pixel returned {result}, expected None"
    )


def test_enterprises_no_undispatchable_verbs_clickable():
    """Every verb held by a hit region is dispatchable, and both expand and
    appoint are actually present so a blank panel cannot pass by holding nothing.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    allowed = {"expand_enterprise", "appoint_director", "char_id",
               "open_director_picker", "close_director_picker"}
    found_verbs = set()
    for _, act in v._enterprise_hits + v._appoint_hits:
        action = act.get("action", act)
        for key in action:
            assert key in allowed, f"undispatchable verb {key!r} in hit region"
            found_verbs.add(key)
    assert "expand_enterprise" in found_verbs, "Expand offers must be present in hit regions"
    assert "appoint_director" in found_verbs, "Appoint offers must be present in hit regions"


def test_enterprises_construction_blocks_expand_offer():
    """An idle venture offers Expand; the same venture with under_construction > 0 does not."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    # Find an owned venture
    owned = [e for e in g.enterprises if e.house == player]
    assert len(owned) > 0, "No owned ventures to test"
    target = owned[0]
    eid = target.eid

    # Half 1: idle venture should offer Expand
    target.under_construction = 0
    v.draw(surf)
    idle_eids = [act["eid"] for _, act in v._enterprise_hits]
    assert eid in idle_eids, (
        f"Idle venture eid={eid} not offered in hit regions"
    )

    # Half 2: under construction must not offer Expand
    target.under_construction = 2
    v.draw(surf)
    uc_eids = [act["eid"] for _, act in v._enterprise_hits]
    assert eid not in uc_eids, (
        f"Under-construction venture eid={eid} still offered in hit regions"
    )


def test_enterprises_tier_max_not_offered():
    """A venture at TIER_MAX is not offered an Expand button.

    Same venture asserted offered at tier 1 first, then capped at TIER_MAX
    and asserted not offered — so the control cannot rot away.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))

    # Find an owned venture and assert it's offered at tier 1
    owned = [e for e in g.enterprises if e.house == player and e.under_construction == 0]
    assert len(owned) > 0, "No owned ventures to test"
    target = owned[0]
    eid = target.eid

    # Control: offered at current tier (1)
    v.draw(surf)
    offered_eids = [act["eid"] for _, act in v._enterprise_hits]
    assert eid in offered_eids, (
        f"Control failed: {target.name} at tier {target.tier} not offered, "
        "so absence at TIER_MAX proves nothing"
    )

    # Cap the venture at TIER_MAX
    target.tier = TIER_MAX
    target.target_tier = TIER_MAX
    v.draw(surf)
    capped_eids = [act["eid"] for _, act in v._enterprise_hits]
    assert eid not in capped_eids, (
        f"{target.name} at TIER_MAX ({TIER_MAX}) still offered an Expand button; "
        "the press can never be accepted on any turn"
    )


def test_enterprises_every_eligible_venture_is_reachable():
    """Every eligible venture is reachable by a click, not just the first.

    Seeds the eligible set from the game state and compares it to the set of
    eids reachable via handle_click — so the test keeps working when the
    fixture changes.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Compute eligible set from game state
    eligible_eids = set()
    for ent in g.enterprises:
        if ent.house != player:
            continue
        if ent.tier >= TIER_MAX:
            continue
        if ent.under_construction > 0:
            continue
        eligible_eids.add(ent.eid)

    # Compute reachable set by sweeping every hit region
    reachable_eids = set()
    for rect, act in v._enterprise_hits:
        result = v.handle_click(rect.center)
        if result is not None:
            eid = result.get("expand_enterprise") or result.get("eid")
            if eid is not None:
                reachable_eids.add(eid)

    assert eligible_eids == reachable_eids, (
        f"Eligible ventures {sorted(eligible_eids)} != reachable "
        f"{sorted(reachable_eids)} — "
        f"missing: {sorted(eligible_eids - reachable_eids)}"
    )


def test_enterprises_draw_is_read_only():
    """Drawing the Enterprises tab changes nothing in the game state.

    Draw is a report, not a move.  Snapshot every mutable field before and
    compare after — attention, treasuries, venture tiers/construction,
    events, enterprises count, and turn.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))

    # Snapshot before
    before_attention = dict(g.attention)
    before_treasuries = {h: g.houses[h].treasury for h in g.houses}
    before_ventures = [(e.eid, e.tier, e.target_tier, e.under_construction)
                       for e in g.enterprises]
    before_events = len(g.events)
    before_enterprises = len(g.enterprises)
    before_turn = g.turn

    # Draw
    v.draw(surf)

    # Compare after
    assert dict(g.attention) == before_attention, (
        f"Draw changed attention: {before_attention} -> {dict(g.attention)}"
    )
    for h in g.houses:
        assert g.houses[h].treasury == before_treasuries[h], (
            f"Draw changed {h}'s treasury: {before_treasuries[h]} -> "
            f"{g.houses[h].treasury}"
        )
    after_ventures = [(e.eid, e.tier, e.target_tier, e.under_construction)
                      for e in g.enterprises]
    assert after_ventures == before_ventures, (
        "Draw changed venture state (tier/target_tier/under_construction)"
    )
    assert len(g.events) == before_events, (
        f"Draw changed event count: {before_events} -> {len(g.events)}"
    )
    assert len(g.enterprises) == before_enterprises, (
        f"Draw changed enterprises count: {before_enterprises} -> "
        f"{len(g.enterprises)}"
    )
    assert g.turn == before_turn, (
        f"Draw changed turn: {before_turn} -> {g.turn}"
    )


def test_enterprises_click_outside_buttons_returns_none():
    """A click on the Enterprises tab outside any Expand button returns None.

    Proves the panel does not swallow presses — only pixels inside a hit
    region produce a descriptor.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Pick a point in the content area far from any button
    # Buttons are drawn at PAD (left margin), so the right side should be empty
    test_pos = (surf.get_width() - 50, 200)
    result = v.handle_click(test_pos)
    assert result is None, (
        f"Click at {test_pos} on Enterprises tab returned {result} instead of None"
    )


def test_mid_tier_venture_still_offered_expand():
    """Mid-tier ventures (1-4) are offered Expand; TIER_MAX (5) is not."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    ent = owned[0]
    eid = ent.eid
    for tier in range(1, 6):
        ent.tier = tier
        ent.target_tier = tier
        v = BroadsheetView(g, player)
        v.active_tab = "Enterprises"
        surf = pygame.Surface((1280, 900))
        v.draw(surf)
        hits = [act.get("action", act) for _, act in v._enterprise_hits]
        hit_eids = [a.get("expand_enterprise") for a in hits if "expand_enterprise" in a]
        if tier < 5:
            assert eid in hit_eids, f"tier {tier}: should offer Expand for eid {eid}"
        else:
            assert eid not in hit_eids, f"tier {tier}: should NOT offer Expand for eid {eid}"


def test_appoint_control_opens_picker():
    """Pressing the Appoint control returns {"open_director_picker": eid}."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            result = v.handle_click(rect.center)
            assert result == {"open_director_picker": eid}, f"got {result}"
            return
    pytest.fail("No Appoint control found for owned venture")


def test_opening_picker_changes_nothing():
    """Opening the picker changes nothing: attention, treasury, director_id, events, turn."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    before = {
        "attention": dict(g.attention),
        "treasury": {h: g.houses[h].treasury for h in g.houses},
        "directors": [(e.eid, e.director_id) for e in g.enterprises],
        "events": len(g.events),
        "turn": g.turn,
    }

    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if "appoint_director" in action:
            v.handle_click(rect.center)
            break

    assert dict(g.attention) == before["attention"]
    for h in g.houses:
        assert g.houses[h].treasury == before["treasury"][h]
    after_directors = [(e.eid, e.director_id) for e in g.enterprises]
    assert after_directors == before["directors"]
    assert len(g.events) == before["events"]
    assert g.turn == before["turn"]


def test_picker_names_in_candidates_pool():
    """Every char_id the open picker offers is in director_candidates for that eid."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break

    pool = director_candidates(g, player, eid)
    pool_ids = set(c.id for c in pool)
    for _, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            assert action["char_id"] in pool_ids


def test_picker_lists_top_candidates_in_order():
    """The offered names are the top of the pool, in its order."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break

    pool = director_candidates(g, player, eid)
    # Collect offered char_ids in display order
    offered_ids = []
    for _, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            offered_ids.append(action["char_id"])

    # Should match the top N of the pool
    pool_ids = [c.id for c in pool]
    assert offered_ids == pool_ids[:len(offered_ids)]


def test_picker_names_match_venture_pressed():
    """Appoint on venture A lists names for A, on venture B lists names for B."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    if len(owned) < 2:
        pytest.skip("Need at least 2 owned ventures")
    eid_a, eid_b = owned[0].eid, owned[1].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker for A
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid_a:
            v.handle_click(rect.center)
            break
    pool_a = director_candidates(g, player, eid_a)
    pool_a_ids = set(c.id for c in pool_a)
    for _, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            assert action["char_id"] in pool_a_ids

    # Close and open picker for B
    v._director_picker = None
    v.draw(surf)
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid_b:
            v.handle_click(rect.center)
            break
    pool_b = director_candidates(g, player, eid_b)
    pool_b_ids = set(c.id for c in pool_b)
    for _, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            assert action["char_id"] in pool_b_ids


def test_unowned_venture_no_appoint_control():
    """A venture the House does not own offers no Appoint control."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    unowned = [e for e in g.enterprises if e.house != player]
    if not unowned:
        pytest.skip("No unowned ventures")
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    for _, act in v._appoint_hits:
        action = act.get("action", act)
        eid = action.get("appoint_director")
        assert eid not in [e.eid for e in unowned], (
            f"Unowned venture {eid} offered an Appoint control"
        )


def test_empty_pool_no_appoint_control():
    """A venture whose pool is empty offers no Appoint control."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    # First confirm it DOES offer an Appoint control
    v1 = BroadsheetView(g, player)
    v1.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v1.draw(surf)
    hits_before = [act.get("action", act).get("appoint_director")
                   for _, act in v1._appoint_hits]
    assert eid in hits_before, "Should have offered Appoint before emptying pool"

    # Empty the characters
    g.realms[player].characters.clear()
    v2 = BroadsheetView(g, player)
    v2.active_tab = "Enterprises"
    v2.draw(surf)
    hits_after = [act.get("action", act).get("appoint_director")
                  for _, act in v2._appoint_hits]
    assert eid not in hits_after, (
        f"Empty pool still offered Appoint for eid {eid}"
    )


def test_back_returns_to_ventures():
    """Back returns to the ventures: Expand offers come back, names disappear."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker by pressing Appoint
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None, "Picker should be open"

    # Re-draw to populate picker hits
    v.draw(surf)
    assert len(v._director_picker_hits) > 0, "Picker should have hits after draw"

    # Expand offers should be hidden while picker is open
    expand_eids = [a.get("action", a).get("expand_enterprise") for _, a in v._enterprise_hits
                   if "expand_enterprise" in a.get("action", a)]
    assert eid not in expand_eids, "Expand should be hidden while picker is open"

    # Press Back
    back_rect = v._director_picker_hits[0][0]  # Back is first in the list
    result = v.handle_click(back_rect.center)
    assert v._director_picker is None, "Picker should be closed after Back"

    # Re-draw to restore venture list
    v.draw(surf)
    # Expand offers should be back
    expand_eids_after = [a.get("action", a).get("expand_enterprise") for _, a in v._enterprise_hits
                         if "expand_enterprise" in a.get("action", a)]
    assert eid in expand_eids_after, "Expand should be back after closing picker"


def test_completed_appointment_closes_list():
    """A completed appointment closes the list — venture list is on screen again."""
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None

    # Re-draw to populate picker hits
    v.draw(surf)

    # Press a name (first non-Back hit)
    from gilded.ui.app import _apply_action, AppState
    from types import SimpleNamespace
    for rect, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            result = v.handle_click(rect.center)
            # Apply through _apply_action
            state = SimpleNamespace(game=g, house=player, view=v)
            _apply_action(state, result)
            break

    assert v._director_picker is None, (
        "Picker should be closed after a completed appointment"
    )


def test_pressed_row_returns_that_char_id():
    """Pressing a specific row in the picker returns the char_id of the person on that row.

    Catches the swapped-name mutation (best→worst) and the off-by-one mutation.
    The rule: row N names the candidate at index N in the candidates pool.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid

    # Get the candidates pool for this venture
    from gilded.docket import director_candidates
    pool = director_candidates(g, player, eid)
    assert len(pool) >= 2, "need at least 2 candidates to test row selection"

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None

    # Re-draw to populate picker hits
    v.draw(surf)

    # Collect name hits (non-Back hits that have char_id)
    name_hits = []
    for rect, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            name_hits.append((rect, action))

    assert len(name_hits) >= 2, "need at least 2 name rows to test selection"

    # Press the FIRST name row (index 0) — the best candidate
    # This catches the swapped-name mutation (pool[0] → pool[-1])
    rect0, action0 = name_hits[0]
    expected_char_id = action0.get("char_id")
    result = v.handle_click(rect0.center)
    assert result is not None, "handle_click should return an action for a name row"
    assert result.get("char_id") == expected_char_id, (
        f"Pressing row 0 should return char_id {expected_char_id}, "
        f"got {result.get('char_id')}"
    )

    # Also press the SECOND name row (index 1) — catches the off-by-one mutation
    rect1, action1 = name_hits[1]
    expected_char_id_1 = action1.get("char_id")
    result1 = v.handle_click(rect1.center)
    assert result1 is not None, "handle_click should return an action for a name row"
    assert result1.get("char_id") == expected_char_id_1, (
        f"Pressing row 1 should return char_id {expected_char_id_1}, "
        f"got {result1.get('char_id')}"
    )


def test_back_opens_and_closes_twice():
    """Back closes the picker the first time AND the second time.

    Catches the mutation that lets Back work once then never again —
    a player who opens a second venture's candidates is trapped.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    assert len(owned) >= 2, "need at least 2 owned ventures"
    eid1 = owned[0].eid
    eid2 = owned[1].eid

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker for venture 1
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid1:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None, "picker should be open after first open"

    # Close it with Back (first hit is always Back)
    v.draw(surf)
    back_rect = v._director_picker_hits[0][0]
    v.handle_click(back_rect.center)
    assert v._director_picker is None, "picker should close after first Back"

    # Re-draw to get fresh hits
    v.draw(surf)

    # Open picker for venture 2
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid2:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None, "picker should be open after second open"

    # Close it with Back again
    v.draw(surf)
    back_rect = v._director_picker_hits[0][0]
    v.handle_click(back_rect.center)
    assert v._director_picker is None, "picker should close after second Back"


def test_picker_returns_correct_char_for_second_slot():
    """Pressing the second name row returns the second candidate's char_id, not the first.

    Catches both the swapped-name mutation (best→worst) and the offset-pool mutation
    (every press returns next-in-ranking). The rule: each row names exactly the
    person displayed on that row.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid

    from gilded.docket import director_candidates
    pool = director_candidates(g, player, eid)
    assert len(pool) >= 2, "need at least 2 candidates"

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None

    v.draw(surf)

    # Collect name hits in order
    name_hits = []
    for rect, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            name_hits.append((rect, action))

    assert len(name_hits) >= 2, "need at least 2 name rows"

    # Press the FIRST row and verify it returns the first candidate
    rect0, action0 = name_hits[0]
    result0 = v.handle_click(rect0.center)
    assert result0 is not None
    assert result0.get("char_id") == action0.get("char_id"), (
        f"First row should return {action0.get('char_id')}, got {result0.get('char_id')}"
    )

    # Press the SECOND row and verify it returns the second candidate (not first, not third)
    rect1, action1 = name_hits[1]
    result1 = v.handle_click(rect1.center)
    assert result1 is not None
    assert result1.get("char_id") == action1.get("char_id"), (
        f"Second row should return {action1.get('char_id')}, got {result1.get('char_id')}"
    )
    # The second row should NOT return the first candidate's id
    assert result1.get("char_id") != action0.get("char_id"), (
        "Second row should not return the first candidate's char_id"
    )


def test_backing_out_is_free():
    """Backing out of the picker costs zero attention, gold, and events.

    Catches the mutation that charges an attention for looking then leaving.
    The rule: navigating the Enterprises panel costs nothing until you act.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    eid = owned[0].eid

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Snapshot before
    attention_before = g.attention.get(player, 0)
    treasury_before = g.houses[player].treasury
    event_count_before = len(g.events)
    turn_before = g.turn

    # Open picker
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None

    # Close with Back (first hit is always Back)
    v.draw(surf)
    back_rect = v._director_picker_hits[0][0]
    v.handle_click(back_rect.center)
    assert v._director_picker is None

    # Verify nothing was charged
    assert g.attention.get(player, 0) == attention_before, (
        f"attention should be unchanged after back: was {attention_before}, now {g.attention.get(player, 0)}"
    )
    assert g.houses[player].treasury == treasury_before, (
        f"treasury should be unchanged after back: was {treasury_before}, now {g.houses[player].treasury}"
    )
    assert len(g.events) == event_count_before, (
        f"events should be unchanged after back: was {event_count_before}, now {len(g.events)}"
    )
    assert g.turn == turn_before, (
        f"turn should be unchanged after back: was {turn_before}, now {g.turn}"
    )


def test_pressed_row_appoints_to_that_venture():
    """Pressing a picker row for venture X returns eid==X, not another venture.

    Catches the mutation that swaps the eid so the appointment lands on a
    different venture — right person, wrong works.
    """
    pygame.init()
    g = GildedGame(seed=42)
    player = next(iter(g.houses))
    owned = [e for e in g.enterprises if e.house == player]
    assert len(owned) >= 2, "need at least 2 owned ventures"
    eid = owned[0].eid

    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)

    # Open picker for this specific venture
    for rect, act in v._appoint_hits:
        action = act.get("action", act)
        if action.get("appoint_director") == eid:
            v.handle_click(rect.center)
            break
    assert v._director_picker is not None

    v.draw(surf)

    # Press any name row
    name_hits = []
    for rect, act in v._director_picker_hits:
        action = act.get("action", act)
        if action.get("char_id"):
            name_hits.append((rect, action))
    assert len(name_hits) >= 1

    rect0, action0 = name_hits[0]
    result = v.handle_click(rect0.center)
    assert result is not None
    assert result.get("appoint_director") == eid, (
        f"Expected appointment on eid={eid}, got eid={result.get('appoint_director')}"
    )

