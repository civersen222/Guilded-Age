"""I2d — three checks over the action registry.

CHECK 1a — DRAWN ⊆ ACTIONS: every drawn key is registered (passes).
CHECK 1b — OFFERED ⊆ ACTIONS: every offered key is registered (xfail).
CHECK 1c — OFFERED ⊆ DRAWN: every offered key is drawn (xfail).
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
from gilded.chassis import TurnEvent


# ── CHECK 1 — COVERAGE (three checks) ────────────────────────────────────────


def _offered_keys(view):
    """Return the set of verb keys offered by enterprise_actions()."""
    keys = set()
    for offer in view.enterprise_actions():
        for k in offer.get("action", {}):
            if k != "char_id":
                keys.add(k)
    return keys


def _rich_state():
    """Seed 99 at turn 1 — the only fixture that offers all seven
    enterprise verbs, including defend_buyout (needs an outside
    holder, which seed 42 never acquires)."""
    state = app.new_app_state(seed=99)
    state.game.end_turn()
    offered = _offered_keys(state.view)
    assert offered == {
        "appoint_director", "attack_takeover", "buy_shares",
        "defend_buyout", "expand_enterprise", "found_enterprise",
        "sell_shares",
    }, f"fixture premise moved: offered verbs are {sorted(offered)}"
    return state


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


# ── CHECK 1a — DRAWN ⊆ ACTIONS (passes) ──────────────────────────────────────


def test_every_drawn_key_is_registered():
    """Every key any tab can draw is registered in ACTIONS."""
    state = _rich_state()
    drawn = _collect_emitted_keys(state.view)

    assert drawn == {
        "appoint_director", "close_director_picker", "end_turn",
        "expand_enterprise", "open_director_picker",
        "place_informant", "rule", "select_province", "set_stance",
        "tab", "toggle_narrate",
    }, f"the drawn set moved: {sorted(drawn)}"

    unhandled = sorted(drawn - set(act.ACTIONS))
    assert not unhandled, f"drawn but unhandled: {unhandled}"


# ── CHECK 1b — OFFERED ⊆ ACTIONS (split) ─────────────────────────────────────


def test_exactly_five_offered_verbs_are_unregistered():
    """Pins the CURRENT state by value, and passes today.

    This is the half that can be scored. When Wave I4 registers the
    five, this test goes RED and names what changed -- which is the
    report the xfail below is structurally unable to make."""
    state = _rich_state()
    unregistered = _offered_keys(state.view) - set(act.ACTIONS)
    assert unregistered == {
        "buy_shares", "sell_shares", "found_enterprise",
        "defend_buyout", "attack_takeover",
    }, f"the unregistered set moved: {sorted(unregistered)}"


@pytest.mark.xfail(strict=True, reason=(
    "Five verbs the game OFFERS have no registry entry. Wave I4 wires "
    "them; when it does, this XPASSES and the test above goes red -- "
    "two independent alarms, which is the point of the split."))
def test_every_offered_key_is_registered():
    """Every verb the game offers via enterprise_actions() is in ACTIONS."""
    state = _rich_state()
    unregistered = _offered_keys(state.view) - set(act.ACTIONS)
    assert not unregistered, f"offered but unregistered: {sorted(unregistered)}"


# ── CHECK 1c — OFFERED ⊆ DRAWN (split) ───────────────────────────────────────


def _enterprise_drawn_verbs(view):
    """Verbs the Enterprises tab actually draws, from its hit structures.

    Unwraps the {"label","action","eid"} envelope exactly as
    handle_click does -- `.get("action", payload)`, with the fallback,
    so a bare action dict still works."""
    drawn = set()
    for _rect, payload in list(view._enterprise_hits) + list(view._appoint_hits):
        if isinstance(payload, dict):
            for k in payload.get("action", payload):
                if k != "char_id":
                    drawn.add(k)
    return drawn


def test_exactly_two_enterprise_verbs_are_drawn():
    """Pins the CURRENT state by value, and passes today.

    When Wave I4 draws the five missing verbs, this test goes RED and
    names what changed."""
    state = _rich_state()
    view = state.view
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((800, 600)))

    drawn = _enterprise_drawn_verbs(view)
    assert drawn == {"appoint_director", "expand_enterprise"}, (
        f"the Enterprises tab's drawn verbs moved: {sorted(drawn)}")

    undrawn = _offered_keys(view) - drawn
    assert undrawn == {
        "buy_shares", "sell_shares", "found_enterprise",
        "defend_buyout", "attack_takeover",
    }, f"the undrawn set moved: {sorted(undrawn)}"


@pytest.mark.xfail(strict=True, reason=(
    "The Enterprises tab draws only expand_enterprise and "
    "appoint_director. Five offered verbs are never drawn at all — "
    "they are not dead buttons, they are absent ones. Wave I4 draws "
    "them."))
def test_every_offered_key_is_drawn():
    """Every verb the game offers is actually drawn on screen."""
    state = _rich_state()
    view = state.view
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((800, 600)))

    drawn = _enterprise_drawn_verbs(view)
    undrawn = _offered_keys(view) - drawn
    assert not undrawn, f"offered but never drawn: {sorted(undrawn)}"


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
        return None
    elif key == "open_director_picker":
        owned = [e for e in game.enterprises if e.house == house]
        if owned:
            return {"open_director_picker": owned[0].eid}
        return None
    elif key == "close_director_picker":
        return {"close_director_picker": True}
    elif key == "cycle_exec":
        petitions = game.docket_by_house.get(house, [])
        if petitions:
            return {"cycle_exec": petitions[0].pid}
        return None
    elif key == "tab":
        return {"tab": TABS[0]}
    elif key == "select_province":
        return {"select_province": 0}
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
        pytest.fail(f"No fixture builder for key '{key}'. Every key in "
                    f"ACTIONS must be constructible here — add a branch to "
                    f"_build_action_for_key.")

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
            pytest.fail(f"No fixture builder for key '{key}' where eligible is True. "
                        f"Every key in ACTIONS must be constructible here — add a branch to "
                        f"_build_action_for_key.")

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
        pytest.fail(f"No fixture builder for key '{key}'. Every key in "
                    f"ACTIONS must be constructible here — add a branch to "
                    f"_build_action_for_key.")

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
