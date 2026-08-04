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
        "appoint_director", "close_director_picker", "defend_buyout",
        "end_turn", "expand_enterprise", "open_director_picker",
        "place_informant", "rule", "select_province", "set_stance",
        "tab", "toggle_narrate",
    }, f"the drawn set moved: {sorted(drawn)}"

    unhandled = sorted(drawn - set(act.ACTIONS))
    assert not unhandled, f"drawn but unhandled: {unhandled}"


# ── CHECK 1b — OFFERED ⊆ ACTIONS (split) ─────────────────────────────────────


def test_exactly_two_offered_verbs_are_unregistered():
    """Pins the CURRENT state by value, and passes today.

    This is the half that can be scored. I4b registered defend_buyout, I4d
    registered found_enterprise, taking this from five to two. When a later
    wave registers the rest, this test goes RED and names what changed."""
    state = _rich_state()
    unregistered = _offered_keys(state.view) - set(act.ACTIONS)
    assert unregistered == {
        "buy_shares", "sell_shares",
    }, f"the unregistered set moved: {sorted(unregistered)}"


@pytest.mark.xfail(strict=True, reason=(
    "Two verbs the game OFFERS have no registry entry (buy_shares, sell_shares). "
    "When they are registered, this XPASSES and the test above goes red -- "
    "two independent alarms, which is the point of the split."))
def test_every_offered_key_is_registered():
    """Every verb the game offers via enterprise_actions() is in ACTIONS."""
    state = _rich_state()
    unregistered = _offered_keys(state.view) - set(act.ACTIONS)
    assert not unregistered, f"offered but unregistered: {sorted(unregistered)}"


# ── CHECK 1c — OFFERED ⊆ DRAWN (split) ───────────────────────────────────────


def _enterprise_drawn_verbs(view):
    """Verbs the Enterprises tab actually draws, read from the REGION REGISTRY.

    Migrated in I4b. This used to walk `_enterprise_hits` + `_appoint_hits`,
    the legacy lists I3 superseded. Those lists are now populated only by the
    two buttons that predate the registry, so a button drawn correctly as a
    Region and nothing else was invisible here -- and a census that cannot see
    a new button reports the tab unchanged when it has changed. The registry is
    what the mouse resolves against, so it is what "drawn" means.

    Region.action is already unwrapped by the drawing code, but keep the
    `.get("action", ...)` fallback so a payload envelope still reads correctly.
    """
    drawn = set()
    for r in view.regions._regions:
        group = r.group or ""
        if not (group.startswith("venture:") or group == "house"):
            continue
        payload = r.action
        if isinstance(payload, dict):
            for k in payload.get("action", payload):
                if k != "char_id":
                    drawn.add(k)
    return drawn


def test_exactly_three_enterprise_verbs_are_drawn():
    """Pins the CURRENT state by value, and passes today.

    I4b drew the third, defend_buyout. When a later wave draws the remaining
    four, this test goes RED and names what changed."""
    state = _rich_state()
    view = state.view
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((800, 600)))

    drawn = _enterprise_drawn_verbs(view)
    assert drawn == {"appoint_director", "expand_enterprise", "defend_buyout",
                     "attack_takeover", "found_enterprise"}, (
        f"the Enterprises tab's drawn verbs moved: {sorted(drawn)}")

    undrawn = _offered_keys(view) - drawn
    assert undrawn == {
        "buy_shares", "sell_shares",
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
    elif key == "attack_takeover":
        # Disloyalty is grown, not dealt: at turn 0 the top-threat House has no
        # disloyal kin in ANY seed 42-61 (measured, 0 of 20), so a turn-0
        # fixture can only ever be ineligible. Letting turns elapse -- as the
        # defend_buyout builder does -- makes seed 42 eligible on its third
        # end_turn, with 5.0% for sale and attention intact. The cap of 12 is
        # generous: the slowest seed that ever qualifies needs 11.
        from gilded.intel import threat_rank
        from gilded.society.realm import disloyal_shareholders
        for _ in range(12):
            threats = [x for x in threat_rank(game) if x != house]
            if threats and disloyal_shareholders(game.realms[threats[0]],
                                                 game.enterprises):
                return {"attack_takeover": threats[0]}
            game.end_turn()
        # No seller ever appeared. Still return a WELL-FORMED action naming a
        # real rival rather than None: None means "this verb cannot be
        # constructed at all", while a real action against a loyal House is
        # merely INELIGIBLE, which is a legitimate answer.
        threats = [x for x in threat_rank(game) if x != house]
        if threats:
            return {"attack_takeover": threats[0]}
        return None
    elif key == "cycle_exec":
        petitions = game.docket_by_house.get(house, [])
        if petitions:
            return {"cycle_exec": petitions[0].pid}
        return None
    elif key == "defend_buyout":
        # Outside stakes are acquired DURING a turn: at turn 0 not one seed in
        # 42-62 has one (measured, 0 of 20), and seed 42 never acquires one at
        # any turn. So the builder lets a turn elapse -- that makes seed 46
        # eligible, which is what test_dispatchability's seed sweep needs.
        #
        # When no real outside holder exists the builder still returns a
        # WELL-FORMED action naming some outsider, rather than None. None means
        # "this verb cannot be constructed at all" and fails the test outright;
        # a real action against an empty stake is merely INELIGIBLE, which is a
        # legitimate answer that test_eligible_contract is built to accept.
        owned = [e for e in game.enterprises if e.house == house]
        if not owned:
            return None
        game.end_turn()
        hids = {c.id for c in game.realms[house].characters}
        for e in owned:
            for hid, pct in e.ledger.items():
                if hid not in hids and pct > 0:
                    return {"defend_buyout": (e.eid, hid)}
        outsiders = [c.id for hn, r in game.realms.items() if hn != house
                     for c in r.characters]
        if outsiders:
            return {"defend_buyout": (owned[0].eid, outsiders[0])}
        return None
    elif key == "found_enterprise":
        from gilded.ui.actions import _get_available_charters
        charters = _get_available_charters(game, house)
        if charters:
            kind, pid, pname, cost = charters[0]
            return {"found_enterprise": (kind, pid)}
        return None
    elif key == "close_found_picker":
        return {"close_found_picker": True}
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


# ── I4b — the buyout button: drawn, priced honestly, and it moves the shares ──
#
# `defend_buyout` is not a new engine verb. It is `buy_shares` with the
# counterparty and the size already decided: the seller is the outside holder
# the button names, and the size is the whole of that holder's stake. That is
# why it needs no chooser and can land before buy_shares does.


def _venture_regions(view):
    """Every Region the Enterprises tab registered for a venture.

    Reads the REGION REGISTRY, which is what the mouse actually resolves
    against, rather than the legacy `_enterprise_hits` / `_appoint_hits`
    lists that I3 superseded. A button that exists only as a Region is a
    real button; a test that cannot see it would report it absent.
    """
    return [r for r in view.regions._regions
            if (r.group or "").startswith("venture:")]


def _buyout_offer(view):
    """The single defend_buyout offer on the seed-99 fixture, with the
    enterprise and the outside holder it names resolved."""
    offers = [a for a in view.enterprise_actions()
              if "defend_buyout" in a.get("action", {})]
    assert len(offers) == 1, (
        f"fixture premise moved: {len(offers)} buyout offers, expected 1")
    offer = offers[0]
    eid, outside_id = offer["action"]["defend_buyout"]
    game = view.game
    ent = next(e for e in game.enterprises if e.eid == eid)
    return offer, ent, outside_id


def _engine_price(view, ent, outside_id, pct):
    """What the engine will actually charge to move *pct* of *ent* from the
    outside holder to the player's ruler."""
    from gilded.society.shares import priced_transfer
    game = view.game
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    ruler = game.realms[view.house].ruler
    return priced_transfer(ent, by_id[outside_id], ruler, pct,
                           game.market, game, dry_run=True)


def _fund_house(state, amount):
    """Put *amount* in the house treasury and every character's purse.
    
    The buyout now reads from the house treasury (not an individual purse).
    Funding both keeps the helper honest whichever path the engine takes.
    """
    state.game.houses[state.view.house].treasury = amount
    for c in state.game.realms[state.view.house].characters:
        c.gold_reserve = amount


def _buy_executor(state):
    """The person the engine will actually route a share purchase through."""
    from gilded.docket import INITIATIVES
    from gilded.ai import _executor_for
    game = state.game
    return _executor_for(game, game.realms[state.view.house],
                         INITIATIVES["buy_shares"][0])


def test_the_buyout_reads_the_purse_the_engine_will_spend_from():
    """FIND-3. The buyout reads the house treasury, not individual purses.

    Both directions are asserted. Only refusing when the treasury is empty
    would pass for a check that reads either purse; only accepting when the
    treasury is funded would pass for a check that reads neither. Together
    they name one purse and no other.
    """
    state = _rich_state()
    view, game = state.view, state.game
    offer, _ent, _outside_id = _buyout_offer(view)

    # Empty treasury -> must refuse
    game.houses[view.house].treasury = 0.0
    ok, why = act.ACTIONS["defend_buyout"].eligible(game, view.house,
                                                    offer["action"])
    assert not ok, (
        "the buyout was offered despite an empty treasury")
    assert why, "the refusal gave no reason"

    # Funded treasury -> must allow
    game.houses[view.house].treasury = 10_000.0
    ok2, why2 = act.ACTIONS["defend_buyout"].eligible(game, view.house,
                                                      offer["action"])
    assert ok2, (
        f"the buyout was refused while treasury holds 10,000 gold: {why2}")

    # And the dispatch must spend the SAME purse the check read.
    ent = next(e for e in game.enterprises
               if e.eid == offer["action"]["defend_buyout"][0])
    outside_id = offer["action"]["defend_buyout"][1]
    before = ent.ledger.get(outside_id, 0.0)
    before_treasury = game.houses[view.house].treasury
    act.ACTIONS["defend_buyout"].dispatch(game, view.house, view,
                                          offer["action"])
    assert ent.ledger.get(outside_id, 0.0) < before, (
        "the buyout was allowed on 10,000 treasury and then moved nothing; "
        "the dispatch is spending a different purse")
    assert game.houses[view.house].treasury < before_treasury, (
        "the shares moved but treasury was not debited")


def test_the_buyout_quote_is_the_price_the_engine_charges():
    """FIND-2. The button quotes a number; the engine charges another.

    The quote is `share_price(ent, g) * pct`; the engine runs
    `priced_transfer(...)`. They are different functions and they disagree
    by a wide margin on this fixture -- the button was advertising a price
    the game would never ask for.

    Asserted as a PROPERTY, never as a ratio. The size of the disagreement
    is an artifact of `share_price` clamping to its band floor at this
    fixture's market value; a test that pinned the ratio would be pinning
    the fixture, not the rule.
    """
    state = _rich_state()
    view = state.view
    offer, ent, outside_id = _buyout_offer(view)
    pct = ent.ledger.get(outside_id, 0.0)
    assert pct > 0, "fixture premise moved: the outside holder holds nothing"

    expected = _engine_price(view, ent, outside_id, pct)
    assert offer["price"] == pytest.approx(expected, rel=1e-9), (
        f"the button quotes {offer['price']:.4f} but the engine charges "
        f"{expected:.4f} for the same stake")


def test_defend_buyout_is_registered():
    """The verb the button emits has an entry in ACTIONS."""
    state = _rich_state()
    assert "defend_buyout" in act.ACTIONS, (
        f"defend_buyout is offered but unregistered; ACTIONS has "
        f"{sorted(act.ACTIONS)}")


def test_the_buyout_button_is_drawn_on_the_enterprises_tab():
    """A Region carrying the verb exists after a draw."""
    state = _rich_state()
    view = state.view
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((1280, 900)))

    verbs = set()
    for r in _venture_regions(view):
        if isinstance(r.action, dict):
            verbs |= set(r.action)
    assert "defend_buyout" in verbs, (
        f"the buyout button is not on the screen; venture regions carry "
        f"{sorted(verbs)}")


def test_the_buyout_button_explains_itself():
    """I3e's law: every control answers the mouse. Offered -> a hint;
    refused -> a reason. Neither may be blank."""
    state = _rich_state()
    view = state.view
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((1280, 900)))

    from gilded.ui.widgets import RegionState
    found = [r for r in _venture_regions(view)
             if isinstance(r.action, dict) and "defend_buyout" in r.action]
    assert found, "no buyout region to interrogate"
    for r in found:
        text = r.reason if r.state is RegionState.DISABLED else r.hint
        assert text, (
            f"the buyout button says nothing in state {r.state.name}")


def test_buying_out_the_stake_moves_the_shares_and_the_gold():
    """The conservation invariant, which survives a fumble.

    `initiative()` halves the size on a botch, so the amount that moves is
    not fixed. What IS fixed: whatever leaves the outside holder arrives in
    the house, the house pays for it, and the size bought is the WHOLE stake
    the button named -- or half of it on a fumble, never a token slice.
    `ctx.scale` takes exactly two values, 1.0 and 0.5, so `moved >= pct/2` is
    a property of the rule and not a reading of the rng; asserting a fixed
    transfer size instead would be asserting the rng, which any later change
    to call order would break.
    """
    state = _rich_state()
    view, game = state.view, state.game
    _fund_house(state, 10_000.0)
    offer, ent, outside_id = _buyout_offer(view)

    house_ids = {c.id for c in game.realms[view.house].characters}
    before_holder = ent.ledger.get(outside_id, 0.0)
    before_house = sum(v for k, v in ent.ledger.items() if k in house_ids)
    before_treasury = game.houses[view.house].treasury
    assert before_holder > 0, "fixture premise moved: nothing to buy out"

    ok, why = act.ACTIONS["defend_buyout"].eligible(game, view.house,
                                                    offer["action"])
    assert ok, f"the buyout is refused on a house holding 10,000 gold: {why}"
    act.ACTIONS["defend_buyout"].dispatch(game, view.house, view,
                                          offer["action"])

    moved = before_holder - ent.ledger.get(outside_id, 0.0)
    assert moved > 0, "the dispatch moved no shares at all"
    assert moved >= before_holder * 0.5 - 1e-9, (
        f"the button offered to buy out the whole {before_holder:.4f}% stake "
        f"but only {moved:.4f}% moved; a fumble halves it, nothing takes it "
        f"lower")
    gained = sum(v for k, v in ent.ledger.items() if k in house_ids) - before_house
    assert gained == pytest.approx(moved, rel=1e-9), (
        f"{moved:.4f}% left the holder but {gained:.4f}% reached the house")
    after_treasury = game.houses[view.house].treasury
    assert after_treasury < before_treasury, "the shares moved but were free"


def test_the_buyout_costs_one_attention():
    """It is an initiative like any other."""
    state = _rich_state()
    view, game = state.view, state.game
    _fund_house(state, 10_000.0)
    offer, _ent, _outside_id = _buyout_offer(view)

    before = game.attention[view.house]
    act.ACTIONS["defend_buyout"].dispatch(game, view.house, view,
                                          offer["action"])
    assert game.attention[view.house] == before - 1, (
        f"attention went {before} -> {game.attention[view.house]}")


def test_the_buyout_is_refused_when_the_house_cannot_afford_it():
    """A refusal must name the obstacle, not merely deny."""
    state = _rich_state()
    view, game = state.view, state.game
    offer, ent, outside_id = _buyout_offer(view)
    _fund_house(state, 0.0)

    ok, why = act.ACTIONS["defend_buyout"].eligible(game, view.house,
                                                    offer["action"])
    assert not ok, "a penniless house was told it could buy the stake"
    assert why, "the refusal gave no reason"
    assert "gold" in why.lower() or "afford" in why.lower(), (
        f"the refusal does not name money: {why!r}")


def test_the_buyout_is_refused_with_no_attention_left():
    state = _rich_state()
    view, game = state.view, state.game
    _fund_house(state, 10_000.0)
    offer, _ent, _outside_id = _buyout_offer(view)
    game.attention[view.house] = 0

    ok, why = act.ACTIONS["defend_buyout"].eligible(game, view.house,
                                                    offer["action"])
    assert not ok, "a house with no attention was told it could act"
    assert why, "the refusal gave no reason"


def test_a_refused_buyout_is_drawn_greyed_and_carries_the_reason():
    """The refusal reaches the screen, not just the registry."""
    state = _rich_state()
    view, game = state.view, state.game
    _fund_house(state, 0.0)
    view.active_tab = "Enterprises"
    view.draw(pygame.Surface((1280, 900)))

    from gilded.ui.widgets import RegionState
    found = [r for r in _venture_regions(view)
             if isinstance(r.action, dict) and "defend_buyout" in r.action]
    assert found, "the buyout button vanished instead of being refused"
    for r in found:
        assert r.state is RegionState.DISABLED, (
            "a house that cannot pay was offered a live buyout button")
        assert r.reason, "the greyed buyout button carries no reason"


# ── D-5, D-6: page-level button affordability and attention guard ────────────


def test_D5_page_button_enabled_when_cheapest_affordable():
    """D-5: Page-level found button is ENABLED when treasury is between
    cheapest and dearest charter (cheapest 250, dearest 800).
    
    Uses treasury=260 (between 250 and 800) so the button should be enabled
    because the house can afford at least the cheapest charter."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    from gilded.ui.actions import _get_available_charters
    
    g = GildedGame(seed=42)
    player = g.houses.keys().__iter__().__next__()
    # Find the player-controlled house (not AI)
    for h in g.houses:
        player = h
        break
    
    charters = _get_available_charters(g, player)
    assert len(charters) > 0, "need charters to measure affordability"
    costs = [c[3] for c in charters]
    cheapest = min(costs)
    dearest = max(costs)
    assert cheapest < dearest, "need different cheapest/dearest to discriminate"
    
    # Set treasury between cheapest and dearest
    g.houses[player].treasury = cheapest + 10
    # Ensure attention is available
    g.attention[player] = 3
    
    ok, why = act.ACTIONS["found_enterprise"].eligible(g, player, {"found_enterprise": True})
    assert ok, f"button should be enabled at treasury {cheapest + 10} (cheapest={cheapest}): {why}"


def test_D6_no_attention_refuses_found_enterprise():
    """D-6: A house with no attention is refused found_enterprise."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    
    g = GildedGame(seed=42)
    player = list(g.houses.keys())[0]
    g.houses[player].treasury = 2000.0
    g.attention[player] = 0
    
    ok, why = act.ACTIONS["found_enterprise"].eligible(g, player, {"found_enterprise": True})
    assert not ok, "found_enterprise should be refused with zero attention"
    assert "attention" in why.lower(), f"refusal should mention attention: {why}"


# ── I4d1c: the eight rules the tests do not watch ─────────────────────────────

def test_D1_existing_charter_not_offered():
    """D-1: A charter that already exists is NOT offered (uniqueness rule).
    
    Measured against enterprises the PLAYER owns. Seed 42 turn 0, house Vantrell:
    owned enterprises are estate@13 (Quillvess) and mill@18 (Ulmdale).
    Removing the uniqueness filter would cause estate@13 and mill@18 to reappear."""
    from gilded.tests.test_ui_broadsheet import _enterprises_view
    from gilded.ui.actions import _get_available_charters
    
    g, v = _enterprises_view(seed=42, turns=0)
    charters = _get_available_charters(g, v.house)
    
    # Find the player's own enterprises
    player_enterprises = [e for e in g.enterprises if e.house == v.house]
    # Seed 42 turn 0: exactly 2 — estate@13, mill@18
    assert len(player_enterprises) == 2, f"premise: expected 2 owned enterprises, got {len(player_enterprises)}"
    
    owned_charters = {(e.kind, e.province) for e in player_enterprises}
    offered = {(kind, pid) for kind, pid, pname, cost in charters}
    
    for kind, pid in owned_charters:
        assert (kind, pid) not in offered, (
            f"uniqueness: {kind}@{pid} should NOT be offered — already owned")


def test_D3_header_shows_charter_count():
    """D-3: The chooser header's count is measured from the drawn frame, not from regions.
    
    Substitutes a wrapper for _font to capture every string passed to .render().
    Restores the real _font in a finally block."""
    from gilded.tests.test_ui_broadsheet import _enterprises_view
    from gilded.ui import broadsheet
    from gilded.ui.actions import _get_available_charters
    import sys
    
    g, v = _enterprises_view(seed=42, turns=0)
    charters = _get_available_charters(g, v.house)
    n = len(charters)
    assert n > 0, f"premise: expected charters offered, got {n}"
    
    rendered_strings = []
    real_font = broadsheet._font
    
    class FontWrapper:
        def __init__(self, f):
            self._f = f
        def render(self, text, *args, **kwargs):
            rendered_strings.append(text)
            return self._f.render(text, *args, **kwargs)
        def size(self, text):
            return self._f.size(text)
        def get_linesize(self):
            return self._f.get_linesize()
        def get_height(self):
            return self._f.get_height()
    
    try:
        broadsheet._font = lambda size, **kw: FontWrapper(real_font(size, **kw))
        v._found_picker = True
        surf = pygame.Surface((1280, 900))
        v.draw(surf)
    finally:
        broadsheet._font = real_font
    
    header = [s for s in rendered_strings if "Available Charters" in s]
    assert header, f"no header string drawn; rendered: {rendered_strings[:20]}"
    expected = f"Available Charters ({n})"
    assert expected in header[0], (
        f"header should contain '{expected}': got '{header[0]}'")


def test_D4_row_label_names_province_title_price():
    """D-4: A charter row's drawn label is measured — the label itself, for every row.
    
    The label is f"{province_name} {title} — {cost:.0f} gold".
    Refused rows included. Collects drawn strings via _font wrapper."""
    from gilded.tests.test_ui_broadsheet import _enterprises_view
    from gilded.ui import broadsheet
    from gilded.ui.actions import _get_available_charters
    from gilded.enterprises import KIND_TITLES
    
    g, v = _enterprises_view(seed=42, turns=0)
    charters = _get_available_charters(g, v.house)
    assert len(charters) > 0, "premise: expected charters offered"
    
    rendered_strings = []
    real_font = broadsheet._font
    
    class FontWrapper:
        def __init__(self, f):
            self._f = f
        def render(self, text, *args, **kwargs):
            rendered_strings.append(text)
            return self._f.render(text, *args, **kwargs)
        def size(self, text):
            return self._f.size(text)
        def get_linesize(self):
            return self._f.get_linesize()
        def get_height(self):
            return self._f.get_height()
    
    try:
        broadsheet._font = lambda size, **kw: FontWrapper(real_font(size, **kw))
        v._found_picker = True
        surf = pygame.Surface((1280, 900))
        v.draw(surf)
    finally:
        broadsheet._font = real_font
    
    picker_regions = [r for r in v.regions._regions if r.group == "picker"]
    row_regions = [r for r in picker_regions if "close_found_picker" not in (r.action or {})]
    
    for kind, pid, pname, cost in charters:
        title = KIND_TITLES[kind]
        expected_label = f"{pname} {title} — {cost:.0f} gold"
        found = expected_label in rendered_strings
        assert found, (
            f"label '{expected_label}' not found in rendered strings. "
            f"Rendered samples: {rendered_strings[:30]}")


def test_D7_no_charters_refuses_button():
    """D-7: A house with no charters left is still offered the button — and the state IS reachable.
    
    Seed 42 turn 0, house Vantrell: 9 charters available.
    Appending 9 Enterprise objects empties the list, then the button refuses."""
    from gilded.tests.test_ui_broadsheet import _enterprises_view
    from gilded.ui.actions import _get_available_charters
    from gilded.enterprises import Enterprise, KIND_TITLES
    
    g, v = _enterprises_view(seed=42, turns=0)
    charters = _get_available_charters(g, v.house)
    n = len(charters)
    assert n == 9, f"premise: expected 9 charters, got {n}"
    
    # Fill every available charter with a dummy enterprise
    for kind, pid, pname, cost in charters:
        title = KIND_TITLES[kind]
        ent = Enterprise(
            eid=f"dummy_{kind}_{pid}",
            kind=kind,
            name=f"{pname} {title}",
            house=v.house,
            province=pid,
            tier=1,
            extraction_dial=0,
            director_id=None,
            ledger=None,
            under_construction=False,
            target_tier=1,
        )
        g.enterprises.append(ent)
    
    remaining = _get_available_charters(g, v.house)
    assert len(remaining) == 0, (
        f"premise: expected 0 charters after filling, got {len(remaining)}")
    
    ok, why = act.ACTIONS["found_enterprise"].eligible(g, v.house, {"found_enterprise": True})
    assert not ok, "found_enterprise should be refused when no charters available"
    assert "no charters" in why.lower(), f"refusal should mention no charters: {why}"



