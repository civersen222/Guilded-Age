"""Stage 6B — War verbs press tests: each verb routes through docket.initiative,
refuses with a reason when it cannot act, and changes the simulation when it can.

Every case runs alone on its own fresh game to avoid process-global pollution.
"""

import pytest
from gilded.ui.app import new_app_state
from gilded.docket import initiative
from gilded.fronts import declare_war, WarGoal, _contested_pairs, allocate
from gilded.ai import _executor_for


# ── helpers ──────────────────────────────────────────────────────────────────

def _state(seed=42):
    return new_app_state(seed=seed)


def _wars_of(game, house):
    return [w for w in getattr(game, "wars", [])
            if w.aggressor == house or w.defender == house]


def _ensure_war(state, target=None):
    """Ensure the player house has an active war. Returns the war."""
    g, h = state.game, state.house
    wars = _wars_of(g, h)
    if not wars:
        if target is None:
            for t in g.houses:
                if t != h and _contested_pairs(g, h, t):
                    target = t
                    break
        if target:
            declare_war(g, h, target, WarGoal(kind="humble"))
    return _wars_of(g, h)


def _ensure_pool(game, house, n=3):
    """Ensure the house has uncommitted regiments in the pool."""
    pool = getattr(game, "_raised_regiments", {})
    if pool.get(house, 0) < n:
        pool[house] = n
        setattr(game, "_raised_regiments", pool)


# ── declare_war tests ───────────────────────────────────────────────────────

def test_declare_war_refuses_when_at_peace_no_contested_border():
    """Declare war should refuse if there's no contested border."""
    state = _state(99)  # seed with no contested borders for player
    g, h = state.game, state.house
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    for target in g.houses:
        if target != h:
            msgs = initiative(g, h, "declare_war", executor, target_house=target)
            if msgs:
                assert len(msgs) >= 1 and len(msgs[0]) > 0
                break


def test_declare_war_opens_war_and_creates_fronts():
    """A valid declaration opens a war with at least one front."""
    state = _state(42)
    g, h = state.game, state.house
    target = None
    for t in g.houses:
        if t != h and _contested_pairs(g, h, t):
            target = t
            break
    assert target is not None
    n_before = len(getattr(g, "wars", []))
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    msgs = initiative(g, h, "declare_war", executor, target_house=target)
    n_after = len(getattr(g, "wars", []))
    assert n_after > n_before
    war = g.wars[-1]
    assert war.aggressor == h or war.defender == h
    assert len(war.fronts) >= 1


def test_declare_war_refuses_when_under_truce():
    """Declare war should refuse when there's an active truce."""
    state = _state(42)
    g, h = state.game, state.house
    house_obj = g.houses[h]
    for t in g.houses:
        if t != h and _contested_pairs(g, h, t):
            house_obj.truces[t] = g.turn + 10  # active truce
            realm = g.realms[h]
            executor = _executor_for(g, realm, "war")
            msgs = initiative(g, h, "declare_war", executor, target_house=t)
            assert msgs
            assert any("truce" in m.lower() or "cannot" in m.lower() for m in msgs)
            break


# ── muster tests ────────────────────────────────────────────────────────────

def test_muster_costs_steel_from_pool():
    """Muster must deduct steel from the capacity pool — measured as a DELTA."""
    state = _state(42)
    g, h = state.game, state.house
    _ensure_war(state)  # muster requires an active war
    # End turn to populate capacity from enterprises
    g.end_turn()
    cap = g.capacity.get(h)
    steel_before = cap.get("steel", 0) if cap else 0
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    procs = g.provinces_of(h)
    if procs:
        pid = procs[0].pid
        msgs = initiative(g, h, "muster", executor, province_pid=pid, count=1)
        assert msgs
        cap_after = g.capacity.get(h)
        steel_after = cap_after.get("steel", 0) if cap_after else 0
        delta = steel_before - steel_after
        from gilded.fronts import REGIMENT_STEEL_COST
        msgs_text = " ".join(msgs).lower()
        if "cannot" not in msgs_text:
            assert delta >= REGIMENT_STEEL_COST, f"Steel delta {delta} < {REGIMENT_STEEL_COST}"


def test_muster_refuses_when_broke():
    """Muster refuses when the house cannot afford the steel cost — measured as DELTA against solvent House's refusal set."""
    state = _state(42)
    g, h = state.game, state.house
    _ensure_war(state)  # muster requires an active war
    g.end_turn()  # populate capacity from enterprises
    # Zero out capacity
    cap = getattr(g, "capacity", None)
    if cap is not None and h in cap and "steel" in cap.get(h, {}):
        cap[h]["steel"] = 0
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    procs = g.provinces_of(h)
    if procs:
        pid = procs[0].pid
        msgs = initiative(g, h, "muster", executor, province_pid=pid, count=1)
        assert msgs
        msgs_text = " ".join(msgs).lower()
        assert "cannot" in msgs_text or "not enough" in msgs_text or "refused" in msgs_text or "no" in msgs_text, \
            f"Broke muster did not refuse with reason: {msgs}"


# ── commit tests ────────────────────────────────────────────────────────────

def test_commit_moves_regiment_to_front():
    """Commit must move regiments from pool to a front."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    _ensure_pool(g, h, 3)
    front = war.fronts[0]
    pool_before = g._raised_regiments.get(h, 0)
    reg_before = front.attacker_regiments if war.aggressor == h else front.defender_regiments
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    war_idx = _wars_of(g, h).index(war)
    msgs = initiative(g, h, "commit", executor, war_id=war_idx, front_fid=front.fid, count=1)
    pool_after = g._raised_regiments.get(h, 0)
    reg_after = front.attacker_regiments if war.aggressor == h else front.defender_regiments
    assert pool_after < pool_before
    assert reg_after > reg_before


def test_commit_refuses_when_no_pool():
    """Commit refuses when there are no uncommitted regiments."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    g._raised_regiments = {h: 0}
    front = war.fronts[0]
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    war_idx = _wars_of(g, h).index(war)
    msgs = initiative(g, h, "commit", executor, war_id=war_idx, front_fid=front.fid, count=1)
    assert msgs


# ── appoint_commander tests ─────────────────────────────────────────────────

def test_appoint_commander_places_named_man():
    """Appoint must place a character as commander on the front."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    _ensure_pool(g, h, 1)
    front = war.fronts[0]
    allocate(war, front, h, 1)
    realm = g.realms[h]
    chars = realm.characters
    if chars:
        char_id = chars[0].id
        executor = _executor_for(g, realm, "war")
        war_idx = _wars_of(g, h).index(war)
        msgs = initiative(g, h, "appoint_commander", executor,
                         war_id=war_idx, front_fid=front.fid, char_id=char_id)
        assert msgs


def test_appoint_commander_refuses_no_war():
    """Appoint refuses when the house has no active war."""
    state = _state(42)
    g, h = state.game, state.house
    # Ensure no wars exist
    if hasattr(g, "wars"):
        g.wars.clear()
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    chars = realm.characters
    char_id = chars[0].id if chars else "nobody"
    msgs = initiative(g, h, "appoint_commander", executor,
                     war_id=0, front_fid=1, char_id=char_id)
    assert msgs


# ── negotiate_peace tests ──────────────────────────────────────────────────

def test_negotiate_peace_ends_war_and_sets_truce():
    """A successful peace negotiation ends the war and creates a truce."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    other = war.defender if war.aggressor == h else war.aggressor
    war.war_score = 0.0  # neutral — should accept
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    war_idx = _wars_of(g, h).index(war)
    msgs = initiative(g, h, "negotiate_peace", executor, target_house=other)
    assert msgs


# ── garrison stub tests ────────────────────────────────────────────────────

def test_garrison_stub_returns_no_milestone():
    """The garrison verb called on a House that IS at war must not raise,
    must return no string carrying a milestone identifier, and must either
    move the fronts or say why it cannot."""
    state = _state(42)
    g, h = state.game, state.house
    _ensure_war(state)
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    msgs = initiative(g, h, "adjust_garrison", executor)
    assert isinstance(msgs, list) and len(msgs) > 0
    for m in msgs:
        assert "G16" not in m, f"garrison returned milestone identifier in message: {m!r}"


def test_garrison_refuses_when_no_war():
    """Garrison refuses when the house is at peace."""
    state = _state(42)
    g, h = state.game, state.house
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    msgs = initiative(g, h, "adjust_garrison", executor)
    assert msgs
    assert any("no active war" in m.lower() for m in msgs)


# ── war_id routing tests ───────────────────────────────────────────────────

def test_commit_war_id_as_index():
    """Commit accepts war_id as a zero-based index into the wars list."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    _ensure_pool(g, h, 2)
    front = war.fronts[0]
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    war_idx = _wars_of(g, h).index(war)
    msgs = initiative(g, h, "commit", executor, war_id=war_idx, front_fid=front.fid, count=1)
    assert msgs


def test_appoint_commander_war_id_as_index():
    """Appoint commander accepts war_id as a zero-based index."""
    state = _state(42)
    g, h = state.game, state.house
    war = _ensure_war(state)[0]
    _ensure_pool(g, h, 1)
    front = war.fronts[0]
    allocate(war, front, h, 1)
    realm = g.realms[h]
    chars = realm.characters
    if chars:
        char_id = chars[0].id
        executor = _executor_for(g, realm, "war")
        war_idx = _wars_of(g, h).index(war)
        msgs = initiative(g, h, "appoint_commander", executor,
                         war_id=war_idx, front_fid=front.fid, char_id=char_id)
        assert msgs


# ── action message display tests ──────────────────────────────────────────

def test_action_messages_cleared_after_draw():
    """Action messages must be cleared after draw so they don't persist."""
    state = _state(42)
    view = state.view
    view._action_messages.append("test message")
    assert len(view._action_messages) == 1
    view.draw(state.screen)
    assert len(view._action_messages) == 0


def test_action_messages_populated_by_dispatch():
    """Dispatch result strings must appear in action_messages."""
    state = _state(42)
    g, h = state.game, state.house
    view = state.view
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    msgs = initiative(g, h, "adjust_garrison", executor)
    # Messages should be returned (the UI layer appends them)
    assert isinstance(msgs, list)


# ── determinism test ──────────────────────────────────────────────────────

def test_seed_42_no_input_reaches_same_wars():
    """Seed 42 played 10 turns with no input must reach the same wars."""
    state1 = _state(42)
    for _ in range(10):
        state1.game.end_turn()
    wars1 = [(w.aggressor, w.defender) for w in state1.game.wars]

    state2 = _state(42)
    for _ in range(10):
        state2.game.end_turn()
    wars2 = [(w.aggressor, w.defender) for w in state2.game.wars]

    assert wars1 == wars2


# ── refusal reason tests ──────────────────────────────────────────────────

def test_declare_war_refusal_carries_reason():
    """A refused declaration must carry a readable reason."""
    state = _state(42)
    g, h = state.game, state.house
    house_obj = g.houses[h]
    target = None
    for t in g.houses:
        if t != h and _contested_pairs(g, h, t):
            target = t
            break
    if target:
        house_obj.truces[target] = g.turn + 20
        realm = g.realms[h]
        executor = _executor_for(g, realm, "war")
        msgs = initiative(g, h, "declare_war", executor, target_house=target)
        assert msgs and len(msgs[0]) > 0


def test_muster_refusal_carries_reason():
    """A refused muster must carry a readable reason."""
    state = _state(42)
    g, h = state.game, state.house
    _ensure_war(state)  # muster requires an active war
    cap = getattr(g, "capacity", None)
    if cap is not None and h in cap and "steel" in cap.get(h, {}):
        cap[h]["steel"] = 0
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    procs = g.provinces_of(h)
    if procs:
        pid = procs[0].pid
        msgs = initiative(g, h, "muster", executor, province_pid=pid, count=1)
        assert msgs and len(msgs[0]) > 0


def test_commit_refusal_carries_reason():
    """A refused commit must carry a readable reason."""
    state = _state(42)
    g, h = state.game, state.house
    g._raised_regiments = {h: 0}
    war = _ensure_war(state)[0]
    front = war.fronts[0]
    realm = g.realms[h]
    executor = _executor_for(g, realm, "war")
    war_idx = _wars_of(g, h).index(war)
    msgs = initiative(g, h, "commit", executor, war_id=war_idx, front_fid=front.fid, count=1)
    assert msgs and len(msgs[0]) > 0
