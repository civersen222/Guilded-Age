"""G15 fronts tests: declaring war, mustering, and the grinding line."""

import random

import pytest
from gilded.chassis import GildedGame
from gilded.fronts import (Front, War, WarGoal, allocate, appoint, declare_war,
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
    assert prov.population == pop0 - 3 * 5  # REGIMENT_POP_COST = 5


def test_steel_capacity_gates_the_muster():
    g = _game()
    a, _ = _adjacent_pair(g)
    prov = g.provinces_of(a)[0]
    g.capacity = {a: {"coal": 0.0, "steel": 3.0, "freight": 0.0}}
    raised = raise_regiments(g, a, prov.pid, 5)
    assert raised == 3.0 // 2 == 1  # REGIMENT_STEEL_COST = 2
    assert g.capacity[a]["steel"] == 3.0 - 2  # REGIMENT_STEEL_COST = 2


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
    assert war.war_score == 15.0  # CAPTURE_SCORE
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
    assert g.rng.windows[0] == (0.8, 1.2 + 0.05)  # bold commander: lo=DICE_LO, hi=DICE_HI+TEMPERAMENT_SHIFT
    assert g.rng.windows[1] == (0.8, 1.2)  # the leaderless defense: (DICE_LO, DICE_HI)


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
    assert war.war_score == 100.0  # WAR_SCORE_WIN
    assert any("must come to terms" in m for m in msgs)


def test_militarist_policy_boosts_regiment_power():
    from gilded import policy
    from gilded.chassis import GildedGame
    g = GildedGame(seed=29)
    h = sorted(g.houses)[0]
    g.directives[h].set_stance("war", 100)
    assert policy.effects(g, h).strength_mod > 1.0


# ============================================================================
# GILDED WAVE 11 — the clash: nine rules that decide who advances
# ============================================================================

# --- R1: base battle-luck window with no commander --------------------------

def test_r1_base_dice_window_no_commander():
    """With no commander at all, the dice window is (0.8, 1.2)."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    front.attacker_regiments = 3
    # No commanders appointed on either side
    resolve_front(g, war, front)
    # First window is attacker's dice, second is defender's — both leaderless
    assert g.rng.windows[0] == (0.8, 1.2)
    assert g.rng.windows[1] == (0.8, 1.2)


# --- R2: temperament bar sits at 33.0 --------------------------------------

def test_r2_temperament_bar_exactly_on_threshold():
    """A commander exactly at |bold_craven| = 33.0 triggers the dice colouring."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # Exactly on the bar (bold_craven = 33.0, i.e. bold)
    commander.dispositions["bold_craven"] = 33.0
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Bold >= 33.0 should widen lo: window is (0.8 - 0.05, 1.2) = (0.75, 1.2)
    assert g.rng.windows[0] == (0.75, 1.2)


def test_r2_craven_on_threshold():
    """bold_craven = -33.0 exactly on the bar widens hi by TEMPERAMENT_SHIFT."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # bold_craven = -33.0: bold <= -33.0 branch -> hi += 0.05
    commander.dispositions["bold_craven"] = -33.0
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window: (0.8, 1.2 + 0.05) = (0.8, 1.25)
    assert g.rng.windows[0] == (0.8, 1.25)


def test_r2_craven_one_point_inside():
    """bold_craven = -32.9 is inside the bar — no colouring."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # bold_craven = -32.9: |bold| < 33.0 -> no branch triggered
    commander.dispositions["bold_craven"] = -32.9
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window should be uncoloured: (0.8, 1.2)
    assert g.rng.windows[0] == (0.8, 1.2)


def test_r2_impulsive_on_threshold():
    """patient_impulsive = 33.0 exactly on the bar widens both ends."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # patient_impulsive = 33.0: temper >= 33.0 -> lo -= 0.05, hi += 0.05
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = 33.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window: (0.8 - 0.05, 1.2 + 0.05) = (0.75, 1.25)
    assert g.rng.windows[0] == (0.75, 1.25)


def test_r2_impulsive_one_point_inside():
    """patient_impulsive = 32.9 is inside the bar — no colouring."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # patient_impulsive = 32.9: temper < 33.0 -> no branch triggered
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = 32.9
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window should be uncoloured: (0.8, 1.2)
    assert g.rng.windows[0] == (0.8, 1.2)


def test_r2_patient_on_threshold():
    """patient_impulsive = -33.0 exactly on the bar narrows both ends."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # patient_impulsive = -33.0: temper <= -33.0 -> lo += 0.05, hi -= 0.05
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = -33.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window: (0.8 + 0.05, 1.2 - 0.05) — 0.8+0.05 is not exactly 0.85 in binary float
    assert g.rng.windows[0] == pytest.approx((0.85, 1.15))


def test_r2_patient_one_point_inside():
    """patient_impulsive = -32.9 is inside the bar — no colouring."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # patient_impulsive = -32.9: |temper| < 33.0 -> no branch triggered
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = -32.9
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window should be uncoloured: (0.8, 1.2)
    assert g.rng.windows[0] == (0.8, 1.2)


def test_r2_temperament_bar_one_point_inside():
    """A commander at |bold_craven| = 32.9 does NOT colour the dice."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    # One point inside the bar — should NOT trigger colouring
    commander.dispositions["bold_craven"] = 32.9
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Window should be uncoloured: (0.8, 1.2)
    assert g.rng.windows[0] == (0.8, 1.2)


# --- R3: temperament shift size is 0.05 ------------------------------------

def test_r3_temperament_shift_size():
    """Bold commander shifts lo down by exactly 0.05."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    commander.dispositions["bold_craven"] = 100.0  # deep bold
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Bold: lo is shifted down by 0.05 → (0.75, 1.2)
    assert g.rng.windows[0] == (0.75, 1.2)


# --- R4: bold vs craven bend opposite ways ----------------------------------

def test_r4_craven_widens_the_downside():
    """Craven commander (bold_craven = -100) widens hi, not lo."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    commander.dispositions["bold_craven"] = -100.0  # deep craven
    commander.dispositions["patient_impulsive"] = 0.0
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Craven: hi is shifted up by 0.05 → (0.8, 1.25)
    assert g.rng.windows[0] == (0.8, 1.25)


# --- R5: patient/impulsive moves BOTH ends ----------------------------------

def test_r5_impulsive_widens_both_ends():
    """Deeply impulsive commander (patient_impulsive = +100) widens both ends."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = 100.0  # deeply impulsive
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Impulsive: lo -= 0.05, hi += 0.05 → (0.75, 1.25)
    assert g.rng.windows[0] == (0.75, 1.25)


def test_r5_patient_narrows_both_ends():
    """Deeply patient commander (patient_impulsive = -100) narrows both ends."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    commander.dispositions["bold_craven"] = 0.0
    commander.dispositions["patient_impulsive"] = -100.0  # deeply patient
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Patient: lo += 0.05, hi -= 0.05 → (0.85, 1.15) — allow float epsilon
    lo, hi = g.rng.windows[0]
    assert abs(lo - 0.85) < 1e-9
    assert abs(hi - 1.15) < 1e-9


def test_r5_bold_and_impulsive_combine():
    """Bold + impulsive commander: both spectrums colour the same window."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.aggressor].ruler
    commander.dispositions["bold_craven"] = 100.0  # bold → lo -= 0.05
    commander.dispositions["patient_impulsive"] = 100.0  # impulsive → lo -= 0.05, hi += 0.05
    allocate(war, front, war.aggressor, 3)
    appoint(war, front, war.aggressor, commander)
    resolve_front(g, war, front)
    # Bold: lo -= 0.05; Impulsive: lo -= 0.05, hi += 0.05
    # Combined: lo = 0.8 - 0.05 - 0.05 = 0.7, hi = 1.2 + 0.05 = 1.25
    assert g.rng.windows[0] == (0.7, 1.25)


# --- R6: commander skill multiplier -----------------------------------------

def test_r6_commander_skill_multiplies_power():
    """Command skill multiplies power by 1 + command/30.
    A commander with command=30 gives 2x power; without one it's 1x.
    We choose regiments so the commanded side advances and the uncommanded does not.
    With midpoint dice=1.0 and full supply:
      Attacker: 5 reg * 1.0 mult * supply * 1.0 dice = 5*supply
      Defender: 3 reg * 2.0 mult (cmd=30, div=30) * supply * 1.0 dice = 6*supply
      6 > 5*1.1=5.5 → defender advances"""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    commander = g.realms[war.defender].ruler
    # Set base_stats["command"] = 30 → multiplier = 1 + 30/30 = 2.0
    commander.base_stats["command"] = 30
    front.attacker_regiments = 5
    front.defender_regiments = 3
    appoint(war, front, war.defender, commander)
    line0 = front.line
    resolve_front(g, war, front)
    # Defender wins: line moves toward -1.0
    assert front.line == line0 - 0.25


# --- R7: margin needed to push the line (ADVANCE_EDGE = 1.1) ---------------

def test_r7_attacker_margin_under_ratio_no_advance():
    """Attacker power just under 1.1x defender → line holds, both dig in."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    # MidpointRng returns midpoint of dice window = (0.8+1.2)/2 = 1.0
    # Full supply, no commanders, no entrenchment
    # Attacker: 10 regiments → power = 10 * 1.0 * 1.0 * 1.0 = 10.0
    # Defender: 10 regiments → power = 10 * 1.0 * 1.0 * 1.0 = 10.0
    # 10.0 <= 10.0 * 1.1 = 11.0 → no advance
    # 10.0 <= 10.0 * 1.1 = 11.0 → no advance
    front.attacker_regiments = 10
    front.defender_regiments = 10
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    line0 = front.line
    resolve_front(g, war, front)
    assert front.line == line0
    assert front.entrenchment_a == 1
    assert front.entrenchment_d == 1


def test_r7_attacker_margin_over_ratio_advances():
    """Attacker power just over 1.1x defender → attacker advances."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    # Attacker: 12 regiments → power = 12.0
    # Defender: 10 regiments → power = 10.0
    # 12.0 > 10.0 * 1.1 = 11.0 → attacker advances
    # 10.0 <= 12.0 * 1.1 = 13.2 → defender does not advance
    front.attacker_regiments = 12
    front.defender_regiments = 10
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    front.line = 0.0
    resolve_front(g, war, front)
    assert front.line == 0.25


def test_r7_defender_margin_under_ratio_no_advance():
    """Defender power just under 1.1x attacker → line holds."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    # Attacker: 10 regiments → power = 10.0
    # Defender: 10 regiments → power = 10.0
    # 10.0 <= 10.0 * 1.1 → defender does not advance
    front.attacker_regiments = 10
    front.defender_regiments = 10
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    line0 = front.line
    resolve_front(g, war, front)
    assert front.line == line0
    assert front.entrenchment_a == 1
    assert front.entrenchment_d == 1


def test_r7_defender_margin_over_ratio_advances():
    """Defender power just over 1.1x attacker → defender advances."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    # Attacker: 10 regiments → power = 10.0
    # Defender: 12 regiments → power = 12.0
    # 12.0 > 10.0 * 1.1 = 11.0 → defender advances
    front.attacker_regiments = 10
    front.defender_regiments = 12
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    front.line = 0.0
    resolve_front(g, war, front)
    assert front.line == -0.25


# --- R8: defender pushes line by same step (0.25) --------------------------

def test_r8_defender_advances_same_step():
    """When defender wins, line moves by 0.25 toward -1.0 (same step as attacker)."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    front.attacker_regiments = 10
    front.defender_regiments = 12  # defender stronger → defender advances
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    front.line = 0.0
    resolve_front(g, war, front)
    # Defender pushes: line goes from 0.0 to -0.25
    assert front.line == -0.25


# --- R9: empty theatre does nothing ----------------------------------------

def test_r9_empty_theatre():
    """A front with no power on either side: line unchanged, entrenchment unchanged, no message."""
    g = _game()
    g.rng = MidpointRng()
    war = _war(g)
    front = war.fronts[0]
    front.attacker_regiments = 0
    front.defender_regiments = 0
    front.line = 0.5
    front.entrenchment_a = 2
    front.entrenchment_d = 1
    msgs = resolve_front(g, war, front)
    assert front.line == 0.5
    assert front.entrenchment_a == 2
    assert front.entrenchment_d == 1
    assert msgs == []
