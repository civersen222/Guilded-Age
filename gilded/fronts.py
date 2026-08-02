"""Fronts (mission G15): war as lines on a map, not stacks of doom.

A war is a goal and a handful of fronts - connected runs of contested
border between two Houses. Regiments are raised from province workforce
and steel capacity, allocated to fronts, and led by real characters whose
command skill and temperament tilt the dice. Each resolution the line
shifts in quarter steps; a line pushed to its limit hands a frontier
province to the winner and moves the war score. Casualties feed province
unrest and the century's rising tide. Peace (G16) flows loser to winner:
provinces, gold, shares - and a truce that binds both signatures."""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from gilded.society.shares import seize_enterprises, transfer_shares

REGIMENT_POP_COST = 5          # thousands of workforce per regiment raised
REGIMENT_STEEL_COST = 2        # steel capacity per regiment
ENTRENCH_MAX = 3
WAR_SCORE_WIN = 100.0

DICE_LO = 0.8                  # base battle-luck window
DICE_HI = 1.2
TEMPERAMENT_BAR = 33.0         # |disposition| that colors a commander's dice
TEMPERAMENT_SHIFT = 0.05       # dice window shift per temperament rule
COMMAND_DIV = 30.0             # cmd multiplier = 1 + command/this
CLASH_RULES = 9                # R1–R9: nine rules of the clash
ADVANCE_EDGE = 1.1             # power ratio needed to push the line
LINE_STEP = 0.25
ENTRENCH_DEFENSE = 0.2         # defender power bonus per entrenchment level
CAPTURE_SCORE = 15.0
SUPPLY_FALLOFF = 0.15          # supply = 1 / (1 + this * hops from capital)
UNREACHABLE_HOPS = 20.0        # supply distance used when no road exists
CASUALTY_LO = 0.02             # fraction of committed regiments lost per clash
CASUALTY_HI = 0.08
CASUALTY_UNREST = 2.0          # unrest per regiment lost, at the home frontier
COMMAND_STRESS = 6             # every resolution weighs on the commander


@dataclass
class WarGoal:
    kind: str                  # "seize" | "open_markets" | "humble" | "survive"
    provinces: List[int] = field(default_factory=list)   # for "seize"


@dataclass
class Front:
    fid: int
    border: List[Tuple[int, int]]   # contested (attacker_pid, defender_pid) pairs
    attacker_regiments: int = 0
    defender_regiments: int = 0
    commander_a_id: str = ""
    commander_d_id: str = ""
    entrenchment_a: int = 0
    entrenchment_d: int = 0
    line: float = 0.0               # -1..1, + = attacker advancing


@dataclass
class War:
    aggressor: str
    defender: str
    goal: WarGoal
    fronts: List[Front]
    war_score: float = 0.0          # -100..100, + = aggressor winning
    started_turn: int = 0


# --- raising and wiring ------------------------------------------------------

def _contested_pairs(game, aggressor: str, defender: str) -> List[Tuple[int, int]]:
    """Every border where the aggressor's land touches the defender's."""
    provinces = game.atlas.provinces
    pairs: List[Tuple[int, int]] = []
    for pid in sorted(provinces):
        p = provinces[pid]
        if p.owner != aggressor:
            continue
        for n in sorted(p.neighbors):
            if provinces[n].owner == defender:
                pairs.append((pid, n))
    return pairs


def declare_war(game, aggressor: str, defender: str, goal: WarGoal) -> War:
    """Open the war: contested border pairs group into connected fronts."""
    pairs = _contested_pairs(game, aggressor, defender)
    groups: List[List[Tuple[int, int]]] = []
    group_pids: List[set] = []
    for pair in pairs:
        hits = [i for i, pids in enumerate(group_pids)
                if pair[0] in pids or pair[1] in pids]
        if not hits:
            groups.append([pair])
            group_pids.append({pair[0], pair[1]})
            continue
        base = hits[0]
        groups[base].append(pair)
        group_pids[base] |= {pair[0], pair[1]}
        for j in reversed(hits[1:]):
            groups[base].extend(groups[j])
            group_pids[base] |= group_pids[j]
            del groups[j]
            del group_pids[j]
    fronts = [Front(fid=i, border=grp) for i, grp in enumerate(groups, 1)]
    war = War(aggressor, defender, goal, fronts, 0.0, game.turn)
    game.houses[aggressor].at_war_with.add(defender)
    game.houses[defender].at_war_with.add(aggressor)
    game.wars.append(war)
    return war


def raise_regiments(game, house: str, province_pid: int, count: int) -> int:
    """Muster from a province: each regiment costs workforce and steel.
    Steel is gated only once the chassis has tallied capacity (a game that
    has not yet resolved a turn musters on stockpiles). Returns the number
    actually raised."""
    province = game.atlas.provinces.get(province_pid)
    if province is None or province.owner != house or count <= 0:
        return 0
    n = min(int(count), province.population // REGIMENT_POP_COST)
    cap = game.capacity.get(house)
    if cap is not None and "steel" in cap:
        n = min(n, int(cap["steel"] // REGIMENT_STEEL_COST))
    if n <= 0:
        return 0
    province.population -= n * REGIMENT_POP_COST
    if cap is not None and "steel" in cap:
        cap["steel"] -= n * REGIMENT_STEEL_COST
    return n


def allocate(war: War, front: Front, house: str, regiments: int) -> None:
    """Commit raised regiments to a front, on whichever side the house fights."""
    n = max(0, int(regiments))
    if house == war.aggressor:
        front.attacker_regiments += n
    elif house == war.defender:
        front.defender_regiments += n


def appoint(war: War, front: Front, house: str, commander) -> None:
    """Give the front a commander - a real character, stress and all."""
    if house == war.aggressor:
        front.commander_a_id = commander.id
    elif house == war.defender:
        front.commander_d_id = commander.id


# --- resolution --------------------------------------------------------------

def supply(game, house: str, front: Front) -> float:
    """Distance strangles armies: rail-weighted hops from the capital to
    the nearest friendly frontier province."""
    capital = game.houses[house].capital
    provinces = game.atlas.provinces
    own = [pid for pair in front.border for pid in pair
           if provinces[pid].owner == house]
    pids = own or [pid for pair in front.border for pid in pair]
    if not pids:
        return 1.0
    d = min(game.atlas.distance(capital, pid) for pid in pids)
    if math.isinf(d):
        d = UNREACHABLE_HOPS
    return 1.0 / (1.0 + SUPPLY_FALLOFF * d)


def _find_commander(game, cid: str):
    if not cid:
        return None
    for h in sorted(game.realms):
        for c in game.realms[h].characters:
            if c.id == cid and c.is_alive:
                return c
    return None


def _dice(game, commander) -> float:
    """Battle luck, colored by temperament: the bold widen the upside, the
    craven the downside; the impulsive gamble wider, the patient steadier."""
    lo, hi = DICE_LO, DICE_HI
    if commander is not None:
        bold = commander.dispositions.get("bold_craven", 0.0)
        if bold <= -TEMPERAMENT_BAR:
            hi += TEMPERAMENT_SHIFT
        elif bold >= TEMPERAMENT_BAR:
            lo -= TEMPERAMENT_SHIFT
        temper = commander.dispositions.get("patient_impulsive", 0.0)
        if temper >= TEMPERAMENT_BAR:
            lo -= TEMPERAMENT_SHIFT
            hi += TEMPERAMENT_SHIFT
        elif temper <= -TEMPERAMENT_BAR:
            lo += TEMPERAMENT_SHIFT
            hi -= TEMPERAMENT_SHIFT
    return game.rng.uniform(lo, hi)


def _cmd_mult(commander) -> float:
    if commander is None:
        return 1.0
    return 1.0 + commander.get_effective_stat("command") / COMMAND_DIV


def _bleed(game, war: War, front: Front, house: str, regiments: int) -> Tuple[int, str]:
    """One side's butcher's bill: regiments lost, unrest at the home
    frontier, and a heavier tide."""
    frac = game.rng.uniform(CASUALTY_LO, CASUALTY_HI)
    losses = min(regiments, int(round(regiments * frac)))
    if losses <= 0:
        return 0, ""
    provinces = game.atlas.provinces
    home = [pid for pair in front.border for pid in pair
            if provinces[pid].owner == house]
    if home:
        provinces[min(home)].unrest += CASUALTY_UNREST * losses
    tide = getattr(game, "tide", None)
    if tide is not None and hasattr(tide, "record_atrocity"):
        tide.record_atrocity("war")
    return losses, f"House {house} loses {losses} regiments"


def _capture(game, war: War, front: Front, winner: str, loser: str,
             score: float) -> List[str]:
    """A broken line hands over a frontier province and moves the score."""
    provinces = game.atlas.provinces
    targets = [pid for pair in front.border for pid in pair
               if provinces[pid].owner == loser]
    if not targets:
        front.line = 0.0
        return []
    pid = min(targets)
    provinces[pid].owner = winner
    war.war_score += score
    front.line = 0.0
    front.entrenchment_a = 0
    front.entrenchment_d = 0
    old_pids = {p for pair in front.border for p in pair} | {pid}
    front.border = [pair for pair in _contested_pairs(game, war.aggressor,
                                                      war.defender)
                    if pair[0] in old_pids or pair[1] in old_pids]
    return [f"Front {front.fid}: {provinces[pid].name} falls to House {winner}"]


def resolve_front(game, war: War, front: Front) -> List[str]:
    """One turn of grinding on one front."""
    msgs: List[str] = []
    cmd_a = _find_commander(game, front.commander_a_id)
    cmd_d = _find_commander(game, front.commander_d_id)
    from gilded import policy
    str_a = policy.effects(game, war.aggressor).strength_mod
    str_d = policy.effects(game, war.defender).strength_mod
    power_a = (front.attacker_regiments * _cmd_mult(cmd_a)
               * supply(game, war.aggressor, front) * _dice(game, cmd_a)
               * str_a)
    power_d = (front.defender_regiments * _cmd_mult(cmd_d)
               * supply(game, war.defender, front)
               * (1.0 + ENTRENCH_DEFENSE * front.entrenchment_d)
               * _dice(game, cmd_d) * str_d)
    if power_a <= 0.0 and power_d <= 0.0:
        return msgs                      # an empty theater; nobody marches
    if power_a > power_d * ADVANCE_EDGE:
        front.line = min(1.0, front.line + LINE_STEP)
        front.entrenchment_d = 0
        msgs.append(f"Front {front.fid}: House {war.aggressor}'s line advances")
    elif power_d > power_a * ADVANCE_EDGE:
        front.line = max(-1.0, front.line - LINE_STEP)
        front.entrenchment_a = 0
        msgs.append(f"Front {front.fid}: House {war.defender}'s line advances")
    else:
        front.entrenchment_a = min(ENTRENCH_MAX, front.entrenchment_a + 1)
        front.entrenchment_d = min(ENTRENCH_MAX, front.entrenchment_d + 1)
        msgs.append(f"Front {front.fid}: the line holds; both armies dig in")
    if power_a > 0.0 and power_d > 0.0:
        losses_a, note_a = _bleed(game, war, front, war.aggressor,
                                  front.attacker_regiments)
        losses_d, note_d = _bleed(game, war, front, war.defender,
                                  front.defender_regiments)
        front.attacker_regiments -= losses_a
        front.defender_regiments -= losses_d
        notes = "; ".join(n for n in (note_a, note_d) if n)
        if notes:
            msgs.append(f"Front {front.fid}: {notes}")
    if front.line >= 1.0:
        msgs.extend(_capture(game, war, front, war.aggressor, war.defender,
                             CAPTURE_SCORE))
    elif front.line <= -1.0:
        msgs.extend(_capture(game, war, front, war.defender, war.aggressor,
                             -CAPTURE_SCORE))
    for cmd in (cmd_a, cmd_d):
        if cmd is not None:
            cmd.add_stress(COMMAND_STRESS)
    return msgs


def tick_wars(game) -> List[str]:
    """Resolve every front of every war; call the verdict when the score
    is total or the goal is in hand. Peace itself is signed in G16."""
    msgs: List[str] = []
    for war in list(game.wars):
        for front in war.fronts:
            msgs.extend(resolve_front(game, war, front))
        if (war.goal.kind == "seize" and war.goal.provinces
                and all(game.atlas.provinces[pid].owner == war.aggressor
                        for pid in war.goal.provinces
                        if pid in game.atlas.provinces)):
            war.war_score = WAR_SCORE_WIN
        war.war_score = max(-WAR_SCORE_WIN, min(WAR_SCORE_WIN, war.war_score))
        if war.war_score >= WAR_SCORE_WIN:
            msgs.append(f"House {war.aggressor} holds the whip hand - "
                        f"House {war.defender} must come to terms")
        elif war.war_score <= -WAR_SCORE_WIN:
            msgs.append(f"House {war.defender} has broken the invader - "
                        f"House {war.aggressor} must come to terms")
    return msgs


# --- peace (G16) -------------------------------------------------------------

TRUCE_TURNS = 8
ACCEPT_SCORE = 40.0            # a loser this far down will talk
PROVINCE_SCORE = 15.0          # terms cost: each ceded province
GOLD_SCORE = 50.0              # terms cost: divisor on gold demanded
SHARES_SCORE = 0.3             # terms cost: per pct of shares signed over
MARKETS_SCORE = 10.0           # terms cost: opened markets
TERMS_SCALE = 1.0              # accepted when cost <= score-against * this
OPEN_MARKETS_PRESTIGE = 10.0


@dataclass
class PeaceTerms:
    provinces: List[int] = field(default_factory=list)   # ceded to winner
    gold: float = 0.0
    shares_pct: float = 0.0        # loser's enterprises signed over (via seize/transfer)
    open_markets: bool = False


def _sides(war: War) -> Tuple[str, str]:
    """(winner, loser) by the score; a level score reads for the aggressor."""
    if war.war_score >= 0.0:
        return war.aggressor, war.defender
    return war.defender, war.aggressor


def terms_cost(terms: PeaceTerms) -> float:
    """What the bill weighs, in war-score points."""
    return (PROVINCE_SCORE * len(terms.provinces)
            + terms.gold / GOLD_SCORE
            + SHARES_SCORE * terms.shares_pct
            + (MARKETS_SCORE if terms.open_markets else 0.0))


def ai_acceptable(game, war: War, terms: PeaceTerms, for_house: str) -> bool:
    """Would this House sign? A loser talks once the score against them
    reaches ACCEPT_SCORE, and signs any bill no heavier than the beating."""
    against = -war.war_score if for_house == war.aggressor else war.war_score
    if against < ACCEPT_SCORE:
        return False
    return terms_cost(terms) <= against * TERMS_SCALE


def negotiate_peace(game, war: War, terms: PeaceTerms) -> List[str]:
    """Sign the peace: terms flow from loser to winner, the war ends, and
    a truce binds both Houses until it expires."""
    winner, loser = _sides(war)
    provinces = game.atlas.provinces
    msgs = [f"Peace is signed between House {war.aggressor} "
            f"and House {war.defender}"]
    ceded = set()
    for pid in terms.provinces:
        p = provinces.get(pid)
        if p is not None and p.owner == loser:
            p.owner = winner
            ceded.add(pid)
            msgs.append(f"{p.name} is ceded to House {winner}")
    if terms.gold > 0.0:
        paid = min(terms.gold, game.houses[loser].treasury)
        game.houses[loser].debit(game.turn, "reparations paid", paid)
        game.houses[winner].credit(game.turn, "reparations received", paid)
        msgs.append(f"House {loser} pays {paid:.0f} gold in reparations")
    if terms.shares_pct > 0.0 and ceded:
        spoils = [e for e in game.enterprises
                  if e.house == loser and e.province in ceded]
        if terms.shares_pct >= 100.0:
            taken = seize_enterprises(spoils, loser, winner,
                                      game.realms[winner])
            if taken:
                msgs.append(f"{taken} enterprises re-register "
                            f"under House {winner}")
        elif spoils:
            ruler = game.realms[winner].ruler
            for ent in spoils:
                for holder, stake in sorted(ent.ledger.items()):
                    if holder != ruler.id:
                        transfer_shares(ent, holder, ruler.id,
                                        stake * terms.shares_pct / 100.0)
            msgs.append(f"{terms.shares_pct:.0f}% of the works on the ceded "
                        f"frontier is signed over to House {winner}")
    if terms.open_markets:
        game.houses[winner].prestige += OPEN_MARKETS_PRESTIGE
        msgs.append(f"House {loser}'s markets open to House {winner}'s goods")
    if war in game.wars:
        game.wars.remove(war)
    game.houses[war.aggressor].at_war_with.discard(war.defender)
    game.houses[war.defender].at_war_with.discard(war.aggressor)
    expiry = game.turn + TRUCE_TURNS
    game.houses[war.aggressor].truces[war.defender] = expiry
    game.houses[war.defender].truces[war.aggressor] = expiry
    msgs.append(f"A truce holds until turn {expiry}")
    return msgs
