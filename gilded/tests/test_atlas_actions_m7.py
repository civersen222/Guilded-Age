"""M7 — atlas actions: acquire_minor, build_rail, tour_province.

New test file for Stage 7. Tests the three atlas verbs added to
the action registry.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from gilded.ui import app
from gilded.ui.actions import ACTIONS, _acquire_minor_eligible, _build_rail_eligible, _tour_province_eligible
from gilded.world import MINOR_OWNER


def _atlas_game():
    """Return a game + player house for atlas action tests."""
    pygame.init()
    state = app.new_app_state(seed=42)
    return state.game, state.house


# ── REGISTRY ────────────────────────────────────────────────────────────────


def test_m7_registry_has_acquire_minor():
    """acquire_minor is registered in ACTIONS."""
    assert "acquire_minor" in ACTIONS


def test_m7_registry_has_build_rail():
    """build_rail is registered in ACTIONS."""
    assert "build_rail" in ACTIONS


def test_m7_registry_has_tour_province():
    """tour_province is registered in ACTIONS."""
    assert "tour_province" in ACTIONS


# ── ACQUIRE MINOR ───────────────────────────────────────────────────────────


def test_m7_acquire_minor_refuses_non_minor():
    """acquire_minor refuses a province already owned by a Great House."""
    game, house = _atlas_game()
    # find a province owned by the player house
    for pid, prov in game.atlas.provinces.items():
        if prov.owner == house:
            ok, reason = _acquire_minor_eligible(game, house, {"acquire_minor": pid})
            assert not ok
            assert "flies a Great House" in reason
            return
    pytest.fail("no owned province found")


def test_m7_acquire_minor_refuses_no_border():
    """acquire_minor refuses a minor that does not border any owned province."""
    game, house = _atlas_game()
    owned = {p.pid for p in game.atlas.provinces.values() if p.owner == house}
    # find a minor that doesn't border any owned province
    for pid, prov in game.atlas.provinces.items():
        if prov.owner == MINOR_OWNER and not (prov.neighbors & owned):
            ok, reason = _acquire_minor_eligible(game, house, {"acquire_minor": pid})
            assert not ok
            assert "shares no border" in reason
            return
    pytest.fail("no non-bordering minor found")


def test_m7_acquire_minor_refuses_no_attention():
    """acquire_minor refuses when the House has no attention."""
    game, house = _atlas_game()
    game.attention[house] = 0
    ok, reason = _acquire_minor_eligible(game, house, {"acquire_minor": None})
    assert not ok
    assert "attention" in reason.lower() or "Attention" in reason


# ── BUILD RAIL ──────────────────────────────────────────────────────────────


def test_m7_build_rail_refuses_rail_present():
    """build_rail refuses a link that already has rail."""
    game, house = _atlas_game()
    # links is a dict, iterate values
    rail_links = [l for l in game.atlas.links.values() if l.rail]
    if not rail_links:
        # create a rail link by setting rail=True on a link
        link = next(iter(game.atlas.links.values()))
        link.rail = True
        rail_links = [link]
    for link in rail_links:
        ok, reason = _build_rail_eligible(game, house, {
            "build_rail_a": link.a, "build_rail_b": link.b
        })
        assert not ok
        assert "track" in reason.lower() or "No track" in reason
        return


def test_m7_build_rail_refuses_no_attention():
    """build_rail refuses when the House has no attention."""
    game, house = _atlas_game()
    game.attention[house] = 0
    ok, reason = _build_rail_eligible(game, house, {
        "build_rail_a": None, "build_rail_b": None
    })
    assert not ok


# ── TOUR PROVINCE ───────────────────────────────────────────────────────────


def test_m7_tour_refuses_foreign_province():
    """tour_province refuses a province not owned by the House."""
    game, house = _atlas_game()
    # find a province not owned by the player
    for pid, prov in game.atlas.provinces.items():
        if prov.owner != house:
            ok, reason = _tour_province_eligible(game, house, {"tour_province": pid})
            assert not ok
            assert "does not own" in reason
            return
    pytest.fail("no foreign province found")


def test_m7_tour_refuses_no_attention():
    """tour_province refuses when the House has no attention."""
    game, house = _atlas_game()
    game.attention[house] = 0
    ok, reason = _tour_province_eligible(game, house, {"tour_province": None})
    assert not ok
    assert "attention" in reason.lower() or "Attention" in reason


# ── INITIATIVE ARRIVAL ──────────────────────────────────────────────────────

def test_m7_actions_in_initiative():
    """All three atlas verbs are known to docket.initiative."""
    from gilded.docket import INITIATIVES
    assert "acquire_minor" in INITIATIVES
    assert "build_rail" in INITIATIVES
    assert "tour_province" in INITIATIVES


# ── PRESS TEST ──────────────────────────────────────────────────────────────

def test_m7_build_rail_press_through_apply_action():
    """Press build_rail through _apply_action from the drawn rail row — link.rail flips, treasury falls by RAIL_COST."""
    from gilded.docket import RAIL_COST
    pygame.init()
    state = app.new_app_state(seed=42)
    game = state.game
    house = state.house
    # find a rail-less link between two owned provinces
    for link in game.atlas.links.values():
        if not link.rail and link.a in [pid for pid, p in game.atlas.provinces.items() if p.owner == house] and link.b in [pid for pid, p in game.atlas.provinces.items() if p.owner == house]:
            break
    treasury_before = game.houses[house].treasury
    action = {"build_rail": True, "build_rail_a": link.a, "build_rail_b": link.b}
    app._apply_action(state, action)
    assert link.rail, "link.rail must be True after pressing build_rail"
    assert game.houses[house].treasury == treasury_before - RAIL_COST
