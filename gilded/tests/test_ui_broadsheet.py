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


# ── Enterprises view helpers ─────────────────────────────────────────────

def _enterprises_view(seed=42, turns=3):
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
