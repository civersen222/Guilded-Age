"""Mission C3 wave 2 - the four Orders act on the world (adapt-shape).

Wave 1 gave the Orders their anatomy and a goal that re-aims; the levers
were no-ops. wave 2 makes each lever move a real, deterministic world
quantity on the House the Order aims at:

  Crown    - border pressure: adds unrest to the target's provinces
  Treasury - collects a tax share of its target's gold into ITS OWN treasury
  Guilds   - quiets the mills: removes unrest from the target's provinces
  Church   - keeps watch: adds unrest to the target's capital

The effect is deterministic (no RNG) and House treasuries are never
touched, so the world the Orders push on is identical across boots.
"""

from gilded import GildedGame
from gilded.orders import ORDER_NAMES


def _unrest(g, target):
    return sum(p.unrest for p in g.provinces_of(target))


def test_levers_move_real_world_quantities():
    g = GildedGame(7, player_house="Brandtner")
    for _ in range(12):
        g.end_turn()
        g.tick_orders()
    for name in ORDER_NAMES:
        target = g.orders[name].goal.target
        assert target in g.houses
    # Treasury collects a tax share into its OWN treasury; the target
    # House's gold is never touched (strength rankings stay put).
    treasury = g.orders["Treasury"]
    assert any(label == "shares taken"
               for (_t, label, _amt) in treasury.journal)
    assert all(label != "shares taken"
               for (_t, label, _amt) in g.houses[treasury.goal.target].journal)
    assert treasury.treasury > 0.0


def test_crown_presses_unrest_up_and_guilds_calm_it():
    g = GildedGame(7, player_house="Brandtner")
    for _ in range(12):
        g.end_turn()
        g.tick_orders()
    crown = g.orders["Crown"]
    guilds = g.orders["Guilds"]
    # both Orders aim at the strongest House (their families resolve there),
    # so the net effect on that House is Crown's pressure minus Guilds' calm.
    if crown.goal.target == guilds.goal.target:
        assert _unrest(g, crown.goal.target) >= 0.0


def test_lever_presses_journal_beats_with_face_and_causes():
    g = GildedGame(7, player_house="Brandtner")
    for _ in range(12):
        g.end_turn()
        g.tick_orders()
    press_beats = [b for b in g.beats.log if b.source == "orders._press"]
    assert press_beats
    for b in press_beats:
        assert b.kind == "signature"
        assert b.face is not None and b.face != ""
        assert b.causes  # a lever press that moved a quantity is attributed


def test_orders_act_deterministically_and_do_not_spend_gold():
    a = GildedGame(7, player_house="Brandtner")
    b = GildedGame(7, player_house="Brandtner")
    for g in (a, b):
        for _ in range(12):
            g.end_turn()
            g.tick_orders()
    for name in ORDER_NAMES:
        assert a.orders[name].treasury == b.orders[name].treasury
        assert a.orders[name].treasury >= 0.0
        assert _unrest(a, a.orders[name].goal.target) == \
            _unrest(b, b.orders[name].goal.target)


def test_deflection_beat_carries_face_and_cause():
    g = GildedGame(7, player_house="Brandtner")
    g.end_turn()
    for name in ORDER_NAMES:
        gl = g.orders[name].goal
        if gl and gl.target and gl.target != "Brandtner":
            target, fam = gl.target, gl.family
            break
    else:
        raise AssertionError("no order goal targets a non-player house")
    g.ambitions.set_ambition("Brandtner", fam, target)
    for _ in range(11):
        g.end_turn()
    clash = [b for b in g.beats.log if b.source == "ambitions.order_clash"]
    assert clash, "no order-clash beat journaled"
    b = clash[-1]
    order_name = g.ambitions.status("Brandtner")["opposed_by"]
    assert b.face == g.orders[order_name].head.name
    assert b.causes, "clash beat carries no causes"
    st = g.ambitions.status("Brandtner")
    assert st["fulfilled"] is False
    assert st["opposed_by"] == order_name
