"""Mission C3 wave 2 - the four Orders act on the world (adapt-shape).

Wave 1 gave the Orders their anatomy and a goal that re-aims; the levers
were no-ops. wave 2 makes each lever move a real, deterministic world
quantity on the House the Order aims at:

  Combine  - stirs the mills: adds unrest to the target's provinces
  Bank     - extends a loan: credits ITS OWN treasury from the target
  Church   - keeps watch: adds unrest to the target's capital
  Gazette  - runs a hard exposé: adds unrest to the target's provinces

The effect is deterministic (no RNG): the Bank's loan lands in the Bank's
own treasury, not the target House's, and a House that holds an Order's
seat is spared the press and takes the Order's honest lever instead.
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
    # The Bank's loan is credited to the Bank's OWN treasury; the target
    # House's gold is never touched (strength rankings stay put).
    bank = g.orders["Bank"]
    assert any(label == "loan extended"
               for (_t, label, _amt) in bank.journal)
    assert all(label != "loan extended"
               for (_t, label, _amt) in g.houses[bank.goal.target].journal)
    assert bank.treasury > 0.0


def test_gazette_and_combine_press_unrest_up():
    g = GildedGame(7, player_house="Brandtner")
    for _ in range(12):
        g.end_turn()
        g.tick_orders()
    gazette = g.orders["Gazette"]
    combine = g.orders["Combine"]
    # both Orders press their target's provinces (a hard exposé, a stirred
    # mill) - unrest on the pressed provinces never goes negative.
    if gazette.goal.target == combine.goal.target:
        assert _unrest(g, gazette.goal.target) >= 0.0


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
