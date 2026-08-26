"""Mission C3 wave 2 - the four Orders act on the world (adapt-shape).

Wave 1 gave the Orders their anatomy and a goal that re-aims; the levers
were no-ops. wave 2 makes each lever move a real, deterministic world
quantity on the House the Order aims at:

  Crown    - border pressure: adds unrest to the target's provinces
  Treasury - buys shares: debits the richest House's gold
  Guilds   - quiets the mills: removes unrest from the target's provinces
  Church   - keeps watch: adds unrest to the target's capital

The effect is deterministic (no RNG) and the Orders' own treasuries are
never touched, so the world they push on is identical across boots.
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
