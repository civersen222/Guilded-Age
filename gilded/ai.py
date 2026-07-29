"""AI Houses (mission G18): one brain, the same levers.

The AI ruler plays the identical loop the player does: reads its docket,
spends attention ruling through real executors, occasionally reaches for
an initiative, and resets the House directives from its own convictions.
Nothing here touches state except through docket.rule / docket.initiative
and the fronts peace table - the AI cheats at nothing."""

from typing import Dict, List, Optional, Tuple

from gilded.directives import DIRECTIVE_CONVICTION, DIRECTIVE_KEYS
from gilded.docket import DOMAIN_SEAT, INITIATIVES, _auto_terms, initiative, rule
from gilded.enterprises import ENTERPRISE_TYPES, EXPAND_COST, TIER_MAX
from gilded.fronts import (ACCEPT_SCORE, REGIMENT_POP_COST, PeaceTerms,
                           ai_acceptable)
# opinion_matrix removed — reads through char._society.opinions now
from gilded.agenda import ensure_agenda, goal_domain, goal_initiative

DIRECTIVE_INTERVAL = 10        # turns between directive resets
OPINION_FLOOR = -20            # a minister this sour is not trusted to execute
AMBITION_BAR = 40.0            # ambitious_content beyond this builds
WAR_CONVICTION = 50.0          # militarist conviction beyond this marches
WEAKER = 0.7                   # a neighbor under this fraction of our strength
URGENCY_ESCALATED = 2.0
CONVICTION_DIV = 50.0
AGENDA_PETITION_BONUS = 1.0    # a petition in the goal's domain jumps the queue

POLICY_STEP = 15       # max stance change per dial per turn
DEAD_BAND = 5          # within this of target, leave it alone (friction accrues)
LOW_TREASURY = 200.0   # below this, the house squeezes labor harder
HIGH_UNREST = 25.0     # above this average, ease off to calm the land
LOW_LEGITIMACY = 30.0  # below this, ease off to calm the land

ENDOWMENT_KIND = {v[0]: k for k, v in sorted(ENTERPRISE_TYPES.items())
                  if v[0] is not None}


def _conviction(ruler, domain: str) -> float:
    pair = DIRECTIVE_CONVICTION.get(domain)
    return ruler.dispositions.get(pair, 0.0) if pair else 0.0


def _score_petition(ruler, petition, goal_dom: Optional[str] = None) -> float:
    urgency = URGENCY_ESCALATED if petition.escalated else 1.0
    bonus = AGENDA_PETITION_BONUS if goal_dom == petition.domain else 0.0
    return urgency + bonus + abs(_conviction(ruler, petition.domain)) / CONVICTION_DIV


def _executor_for(game, realm, domain: str):
    """The seat holder carries it out, unless they hate the ruler."""
    seat = DOMAIN_SEAT.get(domain)
    holder = realm.court.positions.get(seat) if seat is not None else None
    if (holder is not None and holder.is_alive
            and holder._society.opinions.get((holder.id, realm.ruler.id), 0) > OPINION_FLOOR):
        return holder
    return realm.ruler


# --- initiatives -------------------------------------------------------------

def _strength(game, house_name: str) -> float:
    pop = sum(p.population for p in game.provinces_of(house_name))
    return pop // REGIMENT_POP_COST + game.houses[house_name].treasury


def _weaker_neighbor(game, house_name: str) -> Optional[str]:
    house = game.houses[house_name]
    neighbors = set()
    for p in game.provinces_of(house_name):
        for n in p.neighbors:
            o = game.atlas.provinces[n].owner
            if o and o != house_name and o in game.houses:
                neighbors.add(o)
    me = _strength(game, house_name)
    for other in sorted(neighbors):
        if other in house.at_war_with:
            continue
        if house.truces.get(other, 0) > game.turn:
            continue
        if _strength(game, other) < WEAKER * me:
            return other
    return None


def _found_spot(game, house_name: str) -> Optional[Tuple[str, int]]:
    options = []
    taken = {(e.kind, e.province) for e in game.enterprises}
    for p in game.provinces_of(house_name):
        for endow, rich in sorted(p.endowments.items()):
            kind = ENDOWMENT_KIND.get(endow)
            if kind is not None and (kind, p.pid) not in taken:
                options.append((-rich, p.pid, kind))
    options.sort()
    if not options:
        return None
    _negrich, pid, kind = options[0]
    return kind, pid


def _pick_initiative(game, house_name: str, realm, goal=None):
    """The goal's signature verb first, then leftover attention by disposition."""
    house = game.houses[house_name]
    ruler = realm.ruler
    # Sell shares if treasury is low — check before goal so it always runs
    if house.treasury < 500:
        for ent in game.enterprises:
            if ent.house == house_name:
                # Find a buyer from rival houses
                for rival in game.realms:
                    if rival == house_name:
                        continue
                    rival_realm = game.realms.get(rival)
                    if rival_realm is None:
                        continue
                    for c in rival_realm.characters:
                        if c.is_alive and c.age >= 16 and c.id != rival_realm.ruler.id:
                            return "sell_shares", {"eid": ent.eid, "buyer_id": c.id, "pct": 5.0}
                break
    if goal is not None:
        sig = goal_initiative(game, house_name, goal)
        if sig is not None:
            return sig
    # Fill an empty Director seat — always worth doing, costs nothing
    from gilded.docket import director_candidates
    for ent in game.enterprises:
        if ent.house == house_name and ent.director_id == "":
            pool = director_candidates(game, house_name, ent.eid)
            if pool:
                return "appoint_director", {"eid": ent.eid, "char_id": pool[0].id}
    if ruler.dispositions.get("ambitious_content", 0.0) > AMBITION_BAR:
        ents = sorted((e for e in game.enterprises
                       if e.house == house_name and e.tier < TIER_MAX
                       and e.under_construction == 0),
                      key=lambda e: (e.tier, e.eid))
        for ent in ents:
            if house.treasury > EXPAND_COST[ent.tier + 1]:
                return "expand_enterprise", {"eid": ent.eid}
        spot = _found_spot(game, house_name)
        if spot is not None:
            kind, pid = spot
            if house.treasury > ENTERPRISE_TYPES[kind][3]:
                return "found_enterprise", {"kind": kind, "province_pid": pid}
 
    if _conviction(ruler, "war") > WAR_CONVICTION and not house.at_war_with:
        target = _weaker_neighbor(game, house_name)
        if target is not None:
            return "declare_war", {"target_house": target}
    adults = [c for c in realm.dynasty.all_characters.values()
              if c.is_alive and c.age >= 16 and c.id != ruler.id]
    if adults:
        suitors = [n for n in sorted(game.houses)
                   if n != house_name and n in game.realms
                   and n not in house.at_war_with]
        if suitors:
            best = max(suitors, key=lambda n: (house.relations.get(n, 0), n))
            return "propose_marriage", {"target_house": best}
    return None


# --- the turn ----------------------------------------------------------------

def _policy_targets(game, house_name) -> dict:
    """Deterministic target stance per dial: ruler conviction baseline +
    circumstance nudges + Stage-2 agenda bias. No rng."""
    realm = game.realms[house_name]
    ruler = realm.ruler
    targets = {k: _conviction(ruler, k) for k in DIRECTIVE_KEYS}

    house = game.houses[house_name]
    provs = game.provinces_of(house_name)
    unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
    legitimacy = game.legitimacy.get(house_name, 50.0)
    at_war = any(house_name in (w.aggressor, w.defender) for w in game.wars)

    if house.treasury < LOW_TREASURY:
        targets["labor"] += 40            # squeeze harder when broke
    if unrest > HIGH_UNREST or legitimacy < LOW_LEGITIMACY:
        targets["labor"] -= 40            # ease the squeeze to calm the land
        targets["capital"] -= 30          # go traditionalist
    if at_war:
        targets["war"] += 50              # mobilize

    goal = game.agendas.get(house_name)
    fam = getattr(goal, "family", None)
    if fam in ("Conquest", "Glory"):
        targets["war"] += 40
    elif fam in ("Buyout", "Dominion"):
        targets["capital"] += 40
        targets["labor"] += 30
    elif fam == "Consolidation":
        targets["labor"] -= 30
        targets["capital"] -= 20
    elif fam == "Dynasty":
        targets["diplomacy"] += 40

    return {k: max(-100, min(100, int(round(v)))) for k, v in targets.items()}


def set_policy(game, house_name) -> None:
    """Drift each dial one bounded step toward its target, but only while the
    gap exceeds the dead-band. Converged dials are left untouched so their
    seated ministers accrue friction exactly as the player's do. No rng."""
    directives = game.directives[house_name]
    targets = _policy_targets(game, house_name)
    for key in DIRECTIVE_KEYS:
        current = directives.stances.get(key, 0)
        target = targets[key]
        gap = target - current
        if abs(gap) <= DEAD_BAND:
            continue                      # converged: do not reset friction
        step = max(-POLICY_STEP, min(POLICY_STEP, gap))
        directives.set_stance(key, current + step)


def ai_turn(game, house_name: str) -> List[str]:
    """The AI ruler's morning: directives, the docket, then ambition."""
    realm = game.realms.get(house_name)
    if realm is None or realm.ruler is None or not realm.ruler.is_alive:
        return []
    ruler = realm.ruler
    msgs: List[str] = []
    goal = ensure_agenda(game, house_name)
    goal_dom = goal_domain(goal) if goal is not None else None
    set_policy(game, house_name)
    docket = list(game.docket_by_house.get(house_name, []))
    docket.sort(key=lambda p: (-_score_petition(ruler, p, goal_dom), p.pid))
    for petition in docket:
        if game.attention.get(house_name, 0) <= 0:
            break
        conviction = _conviction(ruler, petition.domain)
        option = min(petition.options,
                     key=lambda o: abs(o.stance_bias - conviction))
        executor = _executor_for(game, realm, petition.domain)
        game.attention[house_name] -= 1
        msgs.extend(rule(game, petition, option.key, executor))
        game.docket_by_house[house_name].remove(petition)
    if game.attention.get(house_name, 0) > 0:
        choice = _pick_initiative(game, house_name, realm, goal)
        if choice is not None:
            verb, kwargs = choice
            domain, _handler = INITIATIVES[verb]
            game.attention[house_name] -= 1
            msgs.extend(initiative(game, house_name, verb,
                                   _executor_for(game, realm, domain), **kwargs))
    return msgs


def ai_peace_check(game, war) -> Optional[PeaceTerms]:
    """A beaten AI house sues for peace; the player is never signed for."""
    loser = war.defender if war.war_score >= 0.0 else war.aggressor
    if game.houses[loser].is_player:
        return None
    if abs(war.war_score) < ACCEPT_SCORE:
        return None
    terms = _auto_terms(game, war)
    if ai_acceptable(game, war, terms, loser):
        return terms
    return None
