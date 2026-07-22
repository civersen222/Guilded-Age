"""G15 fronts tests: declaring war, mustering, and the grinding line."""

import random

from gilded.chassis import GildedGame
from gilded.fronts import (CAPTURE_SCORE, DICE_HI, DICE_LO, ENTRENCH_MAX,
                           REGIMENT_POP_COST, REGIMENT_STEEL_COST,
                           TEMPERAMENT_SHIFT, WAR_SCORE_WIN, Front, War,
                           WarGoal, allocate, appoint, declare_war,
                           raise_regiments, resolve_front, supply, tick_wars)

SEED = 42


class MidpointRng(random.Random):
    """uniform() returns the window's midpoint; records every window asked."""

    def __init__(self):
        super().__init__(0)
        self.windows = []

    def uniform(self, a, b):
        self.windows.append((a, b))
        return (a + b) / 2.0


def _game() -> GildedGame:
    return GildedGame(SEED)


def _adjacent_pair(g: GildedGame):
    for a in sorted(g.houses):
        for p in g.provinces_of(a):
            for n in sorted(p.neighbors):
                o = g.atlas.provinces[n].owner
                if o and o != a and o in g.houses:
                    return a, o
    raise AssertionError("seed grew no contested borders")


def _war(g: GildedGame):
    a, d = _adjacent_pair(g)
    return declare_war(g, a, d, WarGoal(kind="humble"))


# --- declaring ---------------------------------------------------------------

def test_declare_war_builds_fronts_on_the_contested_border():
    g = _game()
    a, d = _adjacent_pair(g)
    war = declare_war(g, a, d, WarGoal(kind="humble"))
    assert war.fronts and war in g.wars
    assert d in g.houses[a].at_war_with and a in g.houses[d].at_war_with
    for front in war.fronts:
        for apid, dpid in front.border:
            assert g.atlas.provinces[apid].owner == a
            assert g.atlas.provinces[dpid].owner == d
            assert dpid in g.atlas.provinces[apid].neighbors


# --- mustering ---------------------------------------------------------------

def test_raise_regiments_drains_workforce():
    g = _game()
    a, _ = _adjacent_pair(g)
    prov = g.provinces_of(a)[0]
    pop0 = prov.population
    raised = raise_regiments(g, a, prov.pid, 3)
    assert raised == 3
    assert prov.population == pop0 - 3 * REGIMENT_POP_COST


def test_steel_capacity_gates_the_muster():
    g = _game()
    a, _ = _adjacent_pair(g)
    prov = g.provinces_of(a)[0]
    g.capacity = {a: {"coal": 0.0, "steel": 3.0, "freight": 0.0}}
    raised = raise_regiments(g, a, prov.pid, 5)
    assert raised == 3.0 // REGIMENT_STEEL_COST == 1
    assert g.capacity[a]["steel"] == 3.0 - REGIMENT_STEEL_COST


def test_no_mustering_on_foreign_soil():
    g = _game()
    a, d = _adjacent_pair(g)
    theirs = g.provinces_of(d)[0]
    assert raise_regiments(g, a, theirs.pid, 3) == 0


def test_allocate_and_appoint_route_by_side():
    g = _game()
    war = _war(g)
    front = war.fronts[0]
    allocate(war, front, war.aggressor, 4)
    allocate(war, front, war.defender, 2)
    appoint(war, front, war.aggressor, g.realms[war.aggressor].ruler)
    appoint(war, front, war.defender, g.realms[war.defender].ruler)
    assert front.attacker_regiments == 4 and front.defender_regiments == 2
    assert front.commander_a_id == g.realms[war.aggressor].ruler.id
    assert front.commander_d_id == g.realms[war.defender].ruler.id


# --- supply ------------------------------------------------------------------

def test_supply_is_full_at_the_capital_and_thins_with_distance():
    g = _game()
    war = _war(g)
    a = war.aggressor
    capital = g.houses[a].capital
    neighbor = sorted(g.atlas.provinces[capital].neighbors)[0]
    home_front = Front(fid=99, border=[(capital, neighbor)])
    assert supply(g, a, home_front) == 1.0
    assert all(supply(g, a, f) <= 1.0 for f in war.fronts)


# --- the line ----------------------------------------------------------------

def test_unopposed_attacker_advances_a_quarter_step():
    g = _game()
    war = _war(g)
    front = war.fronts[0]
    allocate(war, front, war.aggressor, 3)
    msgs = resolve_front(g, war, front)
    assert front.line == 0.25
    assert any("line advances" in m for m in msgs)


def test_stalemate_digs_both_sides_in():
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    # A capital-to-capital front gives both sides full supply, so equal
    # regiments with midpoint dice grind to a perfect standstill.
    front = Front(fid=7, border=[(g.houses[war.aggressor].capital,
                                  g.houses[war.defender].capital)])
    front.attacker_regiments = 6
    front.defender_regiments = 6
    msgs = resolve_front(g, war, front)
    assert front.line == 0.0
    assert front.entrenchment_a == 1 and front.entrenchment_d == 1
    assert any("dig in" in m for m in msgs)


def test_casualties_feed_unrest_and_the_tide():
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    front.attacker_regiments = 40
    front.defender_regiments = 40
    home = min(pid for pair in front.border for pid in pair
               if g.atlas.provinces[pid].owner == war.aggressor)
    unrest0 = g.atlas.provinces[home].unrest
    atrocities0 = g.tide.atrocities
    resolve_front(g, war, front)
    assert front.attacker_regiments < 40 and front.defender_regiments < 40
    assert g.atlas.provinces[home].unrest > unrest0
    assert g.tide.atrocities > atrocities0


def test_broken_line_hands_over_a_frontier_province():
    g = _game()
    war = _war(g)
    front = war.fronts[0]
    front.attacker_regiments = 5
    front.line = 0.75
    target = min(pid for pair in front.border for pid in pair
                 if g.atlas.provinces[pid].owner == war.defender)
    msgs = resolve_front(g, war, front)
    assert g.atlas.provinces[target].owner == war.aggressor
    assert war.war_score == CAPTURE_SCORE
    assert front.line == 0.0
    assert any("falls to House" in m for m in msgs)


def test_temperament_colors_the_dice_window():
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    bold = g.realms[war.aggressor].ruler
    bold.dispositions["bold_craven"] = -100.0
    bold.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, bold)
    resolve_front(g, war, front)
    assert g.rng.windows[0] == (DICE_LO, DICE_HI + TEMPERAMENT_SHIFT)
    assert g.rng.windows[1] == (DICE_LO, DICE_HI)     # the leaderless defense


def test_every_resolution_weighs_on_the_commander():
    g = _game()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    stress0 = commander.stress
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    assert commander.stress == stress0 + 6


# --- the verdict -------------------------------------------------------------

def test_seize_goal_in_hand_is_a_decisive_verdict():
    g = _game()
    a, d = _adjacent_pair(g)
    target = g.provinces_of(d)[0]
    war = declare_war(g, a, d, WarGoal(kind="seize", provinces=[target.pid]))
    target.owner = a
    msgs = tick_wars(g)
    assert war.war_score == WAR_SCORE_WIN
    assert any("must come to terms" in m for m in msgs)