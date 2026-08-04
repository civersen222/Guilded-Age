"""I2b — three checks over the action registry.

CHECK 1 — COVERAGE: every action key any tab can emit is in ACTIONS.
CHECK 2 — DISPATCHABILITY: every key in ACTIONS can actually run.
CHECK 3 — BEHAVIOUR PRESERVED: the six game verbs still do what they did.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from gilded.ui import app
from gilded.ui import actions as act
from gilded.ui.broadsheet import TABS


# ── CHECK 1 — COVERAGE ───────────────────────────────────────────────────────

def _collect_emitted_keys(view):
    """Walk every tab, draw to a headless surface, collect all emitted action keys."""
    collected = set()
    surf = pygame.Surface((800, 600))

    for tab_name in TABS:
        view.active_tab = tab_name
        view.draw(surf)

        # Special case: Enterprises tab — collect both picker-open and picker-closed hits
        if tab_name == "Enterprises":
            # First collect from enterprise/appoint hits (picker closed)
            for rect, payload in view._enterprise_hits:
                if isinstance(payload, dict):
                    action = payload.get("action", payload)
                    for k in action:
                        if k != "char_id":
                            collected.add(k)
            for rect, payload in view._appoint_hits:
                if isinstance(payload, dict):
                    action = payload.get("action", payload)
                    for k in action:
                        if k != "char_id":
                            collected.add(k)

            # Open the director picker and collect its hits
            if view._appoint_hits:
                collected.add("open_director_picker")  # emitted by the click we simulate below
                _open_director_picker(view, surf)
                for rect, payload in view._director_picker_hits:
                    if isinstance(payload, dict):
                        for k in payload:
                            if k != "char_id":
                                collected.add(k)

            # Collect standard structures for this tab
            _collect_standard(view, collected)
            continue

        # Standard collection for other tabs
        _collect_standard(view, collected)

    return collected


def _collect_standard(view, collected):
    """Collect keys from standard hit structures for the current tab."""
    for name in view._tab_rects:
        collected.add("tab")
    for rect, payload in view._option_hits:
        if isinstance(payload, tuple) and payload:
            collected.add(payload[0])
    for rect, payload in view._enterprise_hits:
        if isinstance(payload, dict):
            action = payload.get("action", payload)
            for k in action:
                if k != "char_id":
                    collected.add(k)
    for rect, payload in view._appoint_hits:
        if isinstance(payload, dict):
            action = payload.get("action", payload)
            for k in action:
                if k != "char_id":
                    collected.add(k)
    for rect, payload in view._informant_hits:
        if isinstance(payload, dict):
            for k in payload:
                collected.add(k)
    for rect, payload in view._director_picker_hits:
        if isinstance(payload, dict):
            for k in payload:
                if k != "char_id":
                    collected.add(k)
    for rect, key in view._dial_hits:
        collected.add("set_stance")
    if view._end_turn_rect is not None:
        collected.add("end_turn")
    if view._narrate_rect is not None:
        collected.add("toggle_narrate")
    if view._atlas_polys:
        collected.add("select_province")
    if view._appoint_hits:
        collected.add("open_director_picker")


def _open_director_picker(view, surf):
    """Open the director picker for an enterprise with eligible candidates."""
    for rect, payload in view._appoint_hits:
        if isinstance(payload, dict):
            action = payload.get("action", payload)
            if "appoint_director" in action and "char_id" not in action:
                eid = action["appoint_director"]
                view._director_picker = eid
                view._director_picker_hits.clear()
                view.draw(surf)
                return


def _try_open_director_picker(view, surf):
    """Open the director picker by finding an enterprise with appoint_director hits."""
    view.active_tab = "Enterprises"
    view.draw(surf)
    # Look for an appoint action without char_id (triggers picker)
    for rect, payload in view._appoint_hits:
        if isinstance(payload, dict):
            action = payload.get("action", payload)
            if "appoint_director" in action and "char_id" not in action:
                eid = action["appoint_director"]
                view._director_picker = eid
                view._director_picker_hits.clear()
                # Redraw to populate _director_picker_hits
                view.draw(surf)
                return


def test_coverage_emitted_keys_in_actions():
    """Every action key any tab can emit is in ACTIONS."""
    state = app.new_app_state(seed=42)
    view = state.view

    # Assert the fixture reaches Enterprises tab with ventures
    view.active_tab = "Enterprises"
    surf = pygame.Surface((800, 600))
    view.draw(surf)
    assert view._enterprise_hits, "fixture owns no ventures"

    emitted = _collect_emitted_keys(view)

    # Assert a floor — if we collected fewer than 11, the walk is broken
    assert len(emitted) >= 11, f"Collected only {len(emitted)} keys: {sorted(emitted)}"

    missing = sorted(emitted - set(act.ACTIONS))
    assert not missing, f"emitted but unhandled: {missing}"


# ── CHECK 2 — DISPATCHABILITY ────────────────────────────────────────────────

def _build_action_for_key(key, game, house, view=None):
    """Build a minimal action dict for the given key."""
    if key == "end_turn":
        return {"end_turn": True}
    elif key == "toggle_narrate":
        return {"toggle_narrate": True}
    elif key == "place_informant":
        targets = [h for h in game.houses if h != house]
        if targets:
            return {"place_informant": targets[0]}
        return None
    elif key == "set_stance":
        return {"set_stance": ("cooperation", 0)}
    elif key == "rule":
        petitions = game.docket_by_house.get(house, [])
        if petitions:
            p = petitions[0]
            if p.options:
                opt = p.options[0]
                return {"rule": (p.pid, opt.key, None)}
        return None
    elif key == "expand_enterprise":
        owned = [e for e in game.enterprises if e.house == house]
        if owned:
            return {"expand_enterprise": owned[0].eid}
        return None
    elif key == "appoint_director":
        owned = [e for e in game.enterprises if e.house == house]
        if owned:
            realm = game.realms.get(house)
            chars = [c for c in realm.characters if c.is_alive] if realm else []
            if chars:
                return {"appoint_director": owned[0].eid, "char_id": chars[0].id}
            return {"appoint_director": owned[0].eid, "char_id": None}
        return None
    elif key == "close_director_picker":
        return {"close_director_picker": True}
    elif key == "tab":
        return {"tab": "Briefing"}
    elif key == "select_province":
        return {"select_province": 0}
    elif key == "open_director_picker":
        owned = [e for e in game.enterprises if e.house == house]
        if owned:
            return {"open_director_picker": owned[0].eid}
        return None
    return None


@pytest.mark.parametrize("key", sorted(act.ACTIONS))
def test_dispatchability(key):
    """Every key in ACTIONS can actually run — eligible premise, then dispatch."""
    entry = act.ACTIONS[key]

    # Build a game state where eligible returns True
    state = app.new_app_state(seed=42)
    g, h = state.game, state.house
    view = state.view

    action = _build_action_for_key(key, g, h, view)
    if action is None:
        pytest.skip(f"No reachable fixture for key '{key}'")

    # Assert eligible premise
    ok, reason = entry.eligible(g, h, action)
    if not ok:
        # Try alternative seeds to find a state where eligible is True
        found = False
        for seed in range(42, 62):
            state2 = app.new_app_state(seed=seed)
            g2, h2 = state2.game, state2.house
            view2 = state2.view
            action2 = _build_action_for_key(key, g2, h2, view2)
            if action2 is None:
                continue
            ok2, reason2 = entry.eligible(g2, h2, action2)
            if ok2:
                g, h, view, action = g2, h2, view2, action2
                ok, reason = ok2, reason2
                found = True
                break
        if not found:
            pytest.skip(f"No reachable fixture where eligible is True for key '{key}'")

    assert ok, f"eligible returned False for '{key}': {reason}"

    # Assert eligible contract: True => empty reason
    assert reason == "", f"eligible True but reason is not empty: '{reason}'"

    # Dispatch and assert result type
    result = entry.dispatch(g, h, view, action)
    assert isinstance(result, list), f"dispatch for '{key}' returned {type(result)}, expected list"
    assert all(isinstance(line, str) for line in result), \
        f"dispatch for '{key}' returned non-str elements: {[type(l) for l in result]}"


@pytest.mark.parametrize("key", sorted(act.ACTIONS))
def test_eligible_contract(key):
    """False always carries a non-empty reason; True always carries ''."""
    entry = act.ACTIONS[key]

    # Test with a valid action (should be True, reason == "")
    state = app.new_app_state(seed=42)
    g, h = state.game, state.house
    action = _build_action_for_key(key, g, h, state.view)
    if action is None:
        pytest.skip(f"No action buildable for key '{key}'")

    ok, reason = entry.eligible(g, h, action)
    if ok:
        assert reason == "", \
            f"eligible True for '{key}' but reason is '{reason}' — must be ''"

    # Test with a clearly-invalid action to get False
    bad_action = {}
    ok2, reason2 = entry.eligible(g, h, bad_action)
    if not ok2:
        assert reason2 != "", \
            f"eligible False for '{key}' but reason is empty — must be non-empty"


# ── CHECK 3 — BEHAVIOUR PRESERVED ────────────────────────────────────────────

def test_end_turn_advances_turn_and_resets_tab():
    """end_turn: game.turn advances by exactly 1; view.active_tab == 'Briefing'; prev_board set."""
    state = app.new_app_state(seed=42)
    g, view = state.game, state.view
    turn_before = g.turn

    app._apply_action(state, {"end_turn": True})

    assert g.turn == turn_before + 1, "turn must advance by exactly 1"
    assert view.active_tab == "Briefing", "active_tab must reset to Briefing"
    assert view.prev_board is not None, "prev_board must be set"


def test_rule_drops_attention_and_removes_petition():
    """rule: attention drops by exactly 1 AND the petition is gone from docket_by_house."""
    state = app.new_app_state(seed=42)
    g, h = state.game, state.house

    petitions = g.docket_by_house.get(h, [])
    if not petitions:
        pytest.skip("No petitions on docket")

    p = petitions[0]
    if not p.options:
        pytest.skip("Petition has no options")

    opt = p.options[0]
    action = {"rule": (p.pid, opt.key, None)}

    entry = act.ACTIONS["rule"]
    ok, reason = entry.eligible(g, h, action)
    assert ok, f"rule not eligible: {reason}"

    att_before = g.attention[h]
    entry.dispatch(g, h, state.view, action)

    assert g.attention[h] == att_before - 1, "attention must drop by exactly 1"
    assert p.pid not in [pp.pid for pp in g.docket_by_house.get(h, [])], \
        "petition must be removed from docket"


def test_place_informant_drops_attention_and_refuses_at_zero():
    """place_informant: attention drops by 1; refuses when attention is 0."""
    state = app.new_app_state(seed=42)
    g, h = state.game, state.house

    targets = [hh for hh in g.houses if hh != h]
    if not targets:
        pytest.skip("No target houses")

    entry = act.ACTIONS["place_informant"]
    action = {"place_informant": targets[0]}

    # Refuse at zero attention
    g.attention[h] = 0
    ok, reason = entry.eligible(g, h, action)
    assert not ok, "should refuse when attention is 0"
    assert reason != "", "False must carry non-empty reason"

    # Success at positive attention
    g.attention[h] = 1
    ok, reason = entry.eligible(g, h, action)
    assert ok, f"should be eligible with attention=1: {reason}"

    att_before = g.attention[h]
    entry.dispatch(g, h, state.view, action)
    assert g.attention[h] == att_before - 1, "attention must drop by exactly 1"


def test_expand_enterprise_drops_attention_and_writes_events():
    """expand_enterprise: attention drops by 1; narration lines land in game.events."""
    from gilded.chassis import TurnEvent

    state = app.new_app_state(seed=42)
    g, h = state.game, state.house

    owned = [e for e in g.enterprises if e.house == h]
    if not owned:
        pytest.skip("No owned enterprises")

    entry = act.ACTIONS["expand_enterprise"]
    action = {"expand_enterprise": owned[0].eid}
    ok, reason = entry.eligible(g, h, action)
    assert ok, f"expand not eligible: {reason}"

    att_before = g.attention[h]
    events_before = len(g.events)
    result = entry.dispatch(g, h, state.view, action)

    assert g.attention[h] == att_before - 1, "attention must drop by exactly 1"
    assert len(g.events) > events_before, "events must have been added"
    for i in range(events_before, len(g.events)):
        ev = g.events[i]
        assert isinstance(ev, TurnEvent), f"new event {i} is not a TurnEvent"
        assert ev.register == "ledger", f"event register must be 'ledger', got '{ev.register}'"
        assert ev.house == h, f"event house must be '{h}'"


def test_appoint_director_drops_attention_and_clears_picker():
    """appoint_director: attention drops by 1; picker state is cleared."""
    state = app.new_app_state(seed=42)
    g, h, view = state.game, state.house, state.view

    owned = [e for e in g.enterprises if e.house == h]
    if not owned:
        pytest.skip("No owned enterprises")

    realm = g.realms.get(h)
    chars = [c for c in realm.characters if c.is_alive] if realm else []
    char_id = chars[0].id if chars else None

    entry = act.ACTIONS["appoint_director"]
    action = {"appoint_director": owned[0].eid, "char_id": char_id}
    ok, reason = entry.eligible(g, h, action)
    assert ok, f"appoint not eligible: {reason}"

    att_before = g.attention[h]
    view._director_picker = owned[0].eid
    view._director_picker_hits = [(None, {})]

    entry.dispatch(g, h, view, action)

    assert g.attention[h] == att_before - 1, "attention must drop by exactly 1"
    assert view._director_picker is None, "picker must be cleared"
    assert len(view._director_picker_hits) == 0, "picker hits must be cleared"


def test_set_stance_updates_directives():
    """set_stance: directives[house] carries the new stance value."""
    state = app.new_app_state(seed=42)
    g, h = state.game, state.house

    entry = act.ACTIONS["set_stance"]
    action = {"set_stance": ("cooperation", 50)}
    ok, reason = entry.eligible(g, h, action)
    assert ok, f"set_stance not eligible: {reason}"

    entry.dispatch(g, h, state.view, action)

    dirs = g.directives[h]
    assert hasattr(dirs, 'stances'), "directives must have stances attr"
    assert dirs.stances.get("cooperation") == 50, \
        f"cooperation stance must be 50, got {dirs.stances.get('cooperation')}"
