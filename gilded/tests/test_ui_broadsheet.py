"""G22 broadsheet screens: tabs, headless draw, and the click actions."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import TABS, BroadsheetView


def _view():
    pygame.init()
    g = GildedGame(seed=42)
    return g, BroadsheetView(g, next(iter(g.houses)))


def test_tabs_shape():
    assert TABS == ("Briefing", "Gazette", "Ledger", "Letters",
                    "Docket", "Atlas", "House")


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


def test_atlas_click_selects_province():
    g, v = _view()
    v.active_tab = "Atlas"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pid = next(iter(g.atlas.provinces))
    c = g.atlas.provinces[pid].center
    result = v.handle_click((int(c[0] * 8), int(c[1] * 8)))
    assert result == {"select_province": pid} and v.selected_pid == pid