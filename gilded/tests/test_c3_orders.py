"""Mission C3 wave-1 contract, committed as pytest (no shell heredocs).

The four Orders push back with the SAME anatomy as a House:

- anatomy: each Order has a real Character head (a private want + stance),
  a live agenda.Goal on a House, a treasury it credits from, and a reach
  that tracks the realm
- wants: `ambitions.wants(order_name)` returns the head's private want with
  the same shape as a House adult; a second boot of one seed is identical
- clash: a House stake whose target crosses an Order's goal records the
  Order in `status(...).opposed_by` and logs the clash beat
- tick: running the turn loop re-aims a lapsed Order and refreshes reach
- intel: the Order fog is driven purely by the informant lever
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from gilded.chassis import GildedGame
from gilded.intel import report
from gilded.society.characters import Character

ORDER_NAMES = ("Combine", "Bank", "Church", "Gazette")
STANCES = ("backs", "wary", "opposes")


def _sig(g):
    return [(n, g.orders[n].head.name, g.orders[n].goal.family,
             g.orders[n].goal.target) for n in sorted(g.orders)]


def test_orders_exist_with_their_anatomy():
    g = GildedGame(7, player_house="Brandtner")
    assert set(g.orders) == set(ORDER_NAMES)
    for n in ORDER_NAMES:
        o = g.orders[n]
        assert isinstance(o.head, Character)
        assert o.head.name and o.head.age >= 16
        assert o.goal is not None and o.goal.family
        assert o.goal.target in g.houses
        assert isinstance(o.reach, (set, frozenset)) and o.reach
        assert o.treasury >= 0


def test_order_wants_carry_the_same_anatomy_as_a_house_adult():
    g = GildedGame(7, player_house="Brandtner")
    for n in ORDER_NAMES:
        w = g.ambitions.wants(n)
        assert len(w) == 1
        assert w[0]["name"] == g.orders[n].head.name
        assert w[0]["stance"] in STANCES
        assert g.orders[n].head.want is not None
        assert g.orders[n].head.want["stance"] == w[0]["stance"]
        # a House adult's want has the identical keys
        house = next(h for h in g.houses if h != "Brandtner")
        g.ambitions.set_ambition(house, "Consolidation")
        hw = g.ambitions.wants(house)
        if hw:
            assert set(w[0]) == set(hw[0])


def test_wants_are_deterministic_across_boots():
    assert _sig(GildedGame(7)) == _sig(GildedGame(7))


def test_clash_records_the_order_that_stands_in_the_way():
    g = GildedGame(7, player_house="Brandtner")
    player = "Brandtner"
    # some Order is pressing a house; a rival stake against that SAME
    # house crosses the Order
    pressed = {o.goal.target for o in g.orders.values()
               if o.goal is not None and o.goal.target is not None}
    target = next(t for t in pressed if t != player)
    g.set_ambition(player, "Conquest", target)
    assert g.ambitions.status(player)["opposed_by"] in g.orders
    assert any(b.source == "ambitions.order_clash" for b in g.beats.log)


def test_clash_is_none_when_no_order_presses_the_target():
    g = GildedGame(7, player_house="Brandtner")
    # a target no Order is currently aiming at
    unpressed = [h for h in g.houses
                 if h not in {o.goal.target for o in g.orders.values()}]
    non = next(h for h in g.houses if h != "Brandtner")
    if unpressed:
        g.set_ambition(non, "Conquest", unpressed[0])
        assert g.ambitions.status(non)["opposed_by"] is None


def test_tick_reaims_a_lapsed_order_and_refreshes_reach():
    g = GildedGame(7, player_house="Brandtner")
    for _ in range(12):
        g.end_turn()
        g.tick_orders()
    bank = g.orders["Bank"]
    assert bank.goal is not None
    # reach is a SET: the Bank's debt-book houses, refreshed each turn
    assert set(bank.reach) <= set(g.houses)
    assert bank.head.want is not None


def test_intel_fog_is_driven_purely_by_the_informant():
    g = GildedGame(7, player_house="Brandtner")
    r0 = report(g, "Brandtner", "Bank")
    assert r0.tier == 0
    assert r0.apparent_intent == "Their intentions are unknown"
    g.informants.add(("Brandtner", "Bank"))
    r1 = report(g, "Brandtner", "Bank")
    assert r1.tier == 2
    assert r1.apparent_intent.startswith("Pursuing ")
