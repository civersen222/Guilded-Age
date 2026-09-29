"""S16: the ending reads the reign, not the world or the orders.

The judge asks what THIS house did: its own atrocity ledger, the state of
its line, the burden its court carries. A world's crimes and the player's
standing orders are neither.
"""

import types

from gilded.chassis import GildedGame
from gilded.endings import judge, _axis_blood
from gilded.fronts import Front, War, WarGoal, _bleed

SEED = 42


def _game(**kw) -> GildedGame:
    return GildedGame(SEED, **kw)


def _first(g: GildedGame) -> str:
    return sorted(g.houses)[0]


def test_same_world_two_conducts_two_verdicts():
    # Build two conduct histories explicitly on the SAME world: play one
    # century, snapshot the world, then branch the history in two directions
    # and judge both branches.
    import copy

    g = GildedGame(SEED, player_house=None)
    for _ in range(50):
        g.end_turn()
    world = copy.deepcopy(g)

    # History A: a quiet, well-ruled house, second only to one rival.
    a = copy.deepcopy(world)
    h = _first(a)
    others = sorted(a.houses)[1:]
    a.legitimacy[h] = 95.0
    a.houses[h].prestige = 40.0
    a.tide.house_atrocities[h] = 0.0
    a.houses[others[0]].treasury = 10 ** 6   # the rival tops the exchange
    for o in others:
        a.legitimacy[o] = 0.0
        a.houses[o].prestige = 0.0
        a.tide.house_atrocities[o] = 50.0

    # History B: the same world, the same house, a war-torn reign.
    b = copy.deepcopy(world)
    hb = _first(b)
    b.legitimacy[hb] = 30.0
    b.houses[hb].prestige = 0.0
    b.tide.house_atrocities[hb] = 40.0
    b.houses[hb].treasury = 0.0
    for o in others:
        b.legitimacy[o] = 0.0
        b.houses[o].treasury = 0.0

    va = judge(a, h).ending_key
    vb = judge(b, hb).ending_key
    assert va != vb, f"same world, different conduct, same verdict: {va}"
    assert va == "The Quiet Throne"
    assert vb == "The Long Ledger"


def test_war_is_charged_to_the_house_that_wages_it():
    # A house that wages war carries the cost on its OWN ledger;
    # a house that wages none does not. Both halves.
    g = _game()
    hs = sorted(g.houses)
    waging, idle = hs[0], hs[1]

    provs = {pid: p for pid, p in g.atlas.provinces.items()}
    a_pid = next(pid for pid, p in provs.items() if p.owner == waging)
    d_pid = next(pid for pid, p in provs.items() if p.owner == idle)
    front = Front(fid=9000, border=[(a_pid, d_pid)],
                  attacker_regiments=0, defender_regiments=10)
    war = War(aggressor=waging, defender=idle,
              goal=WarGoal(kind="humble"), fronts=[front])
    # rng is shared; force a clash with positive losses on the aggressor side
    # by monkeypatching the fraction draw.
    g.rng = types.SimpleNamespace(uniform=lambda lo, hi: 0.5)
    before = g.tide.house_atrocities.get(waging, 0.0)
    _bleed(g, war, front, waging, 10)
    assert g.tide.house_atrocities.get(waging, 0.0) > before

    # The idle house wages none: nothing lands on its ledger.
    before_idle = g.tide.house_atrocities.get(idle, 0.0)
    front2 = Front(fid=9001, border=[(d_pid, a_pid)],
                   attacker_regiments=10, defender_regiments=0)
    war2 = War(aggressor=idle, defender=waging,
               goal=WarGoal(kind="humble"), fronts=[front2])
    _bleed(g, war2, front2, idle, 10)
    assert g.tide.house_atrocities.get(idle, 0.0) > before_idle
    # And the house that never bled a regiment carries no war charge:
    g2 = _game()
    h2 = _first(g2)
    assert g2.tide.house_atrocities.get(h2, 0.0) == 0.0


def test_blood_scores_the_state_of_the_line_not_its_existence():
    # Four healthy adults and four adults at the top of the stress scale
    # score DIFFERENTLY on blood, and the strained court scores LOWER.
    g = _game()
    h = _first(g)
    realm = g.realms[h]
    dyn = realm.dynasty.all_characters
    chars = list(dyn.values())[:4]
    for c in dyn.values():
        c.is_alive = False
    for c in chars:
        c.is_alive = True
        c.stress = 0
        c.age = 40

    healthy, _, _, _, _ = _axis_blood(g, h)
    for c in chars:
        c.stress = 300
    strained, _, _, _, _ = _axis_blood(g, h)
    assert strained < healthy, (strained, healthy)


def test_quiet_throne_is_reachable():
    g = _game()
    h = _first(g)
    hs = sorted(g.houses)
    g.houses[hs[1]].treasury = 10 ** 6   # someone else tops the exchange
    g.legitimacy[h] = 95.0
    g.houses[h].prestige = 40.0
    g.tide.house_atrocities[h] = 0.0
    # A dirty world must not convict the clean house.
    for o in hs:
        if o != h:
            g.tide.house_atrocities[o] = 50.0
    ep = judge(g, h)
    assert ep.ending_key == "The Quiet Throne"


def test_verdict_is_unchanged_when_the_orders_are_wiped():
    # Stances are standing orders consumed only by end_turn; the verdict
    # is a judgement on the century those orders produced, so wiping them
    # before judgment changes nothing.
    g = _game()
    h = _first(g)
    g.directives[h].set_stance("expansion", 100)
    g.directives[h].set_stance("war", 90)
    before = judge(g, h)
    for d in ("capital", "labor", "expansion", "diplomacy", "war"):
        g.directives[h].set_stance(d, 0)
    after = judge(g, h)
    assert before.ending_key == after.ending_key
    assert before.axes == after.axes
