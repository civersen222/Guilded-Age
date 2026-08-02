"""Living Adversaries (Stage 2): every AI House carries a real, multi-turn
GOAL that soft-biases the reactive brain in gilded/ai.py.

A Goal is chosen DETERMINISTICALLY (never game.rng) from the ruler's own
dispositions and the world state, held for a commit window, then
re-evaluated. Selection only READS the game; the sole writer is
ensure_agenda, which stores the chosen goal on game.agendas. Acting on a
goal routes through docket.initiative - the same honest levers the player
uses - so a goal cheats at nothing.

This module must NOT import gilded.ai (ai.py imports us); the few helpers it
needs from the reactive brain are replicated locally."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from gilded.enterprises import ENTERPRISE_TYPES, EXPAND_COST, TIER_MAX
from gilded.intel import _has_marriage_tie

_REGIMENT_POP_COST = 5  # thousands of workforce per regiment (from fronts)

COMMIT_TURNS = 10          # a goal is held this long before re-evaluation

FAMILIES = ("Conquest", "Dominion", "Buyout", "Dynasty",
            "Intrigue", "Glory", "Consolidation")

# family -> the petition domain its ruler leans into (soft petition bias)
FAMILY_DOMAIN = {
    "Conquest": "war",
    "Dominion": "expansion",
    "Buyout": "capital",
    "Dynasty": "diplomacy",
    "Intrigue": "press",
    "Glory": "war",
    "Consolidation": "labor",
}

_ENDOWMENT_KIND = {v[0]: k for k, v in sorted(ENTERPRISE_TYPES.items())
                   if v[0] is not None}


@dataclass(frozen=True)
class Goal:
    family: str
    target: Optional[str]
    opened_turn: int
    commit_turns: int
    why: str


# --- local helpers (replicated so we never import ai.py) ---------------------

def _disp(ruler, key: str) -> float:
    return float(ruler.dispositions.get(key, 0.0))


def _stat(realm, name: str) -> float:
    return max((c.get_effective_stat(name)
                for c in realm.court.positions.values()
                if c and c.is_alive), default=0.0)


def _strength(game, house_name: str) -> float:
    pop = sum(p.population for p in game.provinces_of(house_name))
    return pop // _REGIMENT_POP_COST + game.houses[house_name].treasury


def _bordering(game, house_name: str) -> List[str]:
    out = set()
    for p in game.provinces_of(house_name):
        for n in p.neighbors:
            o = game.atlas.provinces[n].owner
            if o and o != house_name and o in game.houses:
                out.add(o)
    return sorted(out)


def _weakest_neighbor(game, house_name: str) -> Optional[str]:
    house = game.houses[house_name]
    cands = []
    for other in _bordering(game, house_name):
        if other in house.at_war_with:
            continue
        if house.truces.get(other, 0) > game.turn:
            continue
        cands.append((_strength(game, other), other))
    if not cands:
        return None
    cands.sort()
    return cands[0][1]


def _found_spot(game, house_name: str) -> Optional[Tuple[str, int]]:
    taken = {(e.kind, e.province) for e in game.enterprises}
    options = []
    for p in game.provinces_of(house_name):
        for endow, rich in sorted(p.endowments.items()):
            kind = _ENDOWMENT_KIND.get(endow)
            if kind is not None and (kind, p.pid) not in taken:
                options.append((-rich, p.pid, kind))
    if not options:
        return None
    options.sort()
    _r, pid, kind = options[0]
    return kind, pid


def _marriageable(realm, ruler) -> bool:
    return any(c.is_alive and c.age >= 16 and c.id != ruler.id
               for c in realm.dynasty.all_characters.values())


def _richest_rival(game, house_name: str) -> Optional[str]:
    """Buyout target: the House with the most enterprises we could buy into."""
    counts = {}
    for e in game.enterprises:
        if e.house != house_name and e.house in game.houses:
            counts[e.house] = counts.get(e.house, 0) + 1
    if not counts:
        return None
    return sorted(counts, key=lambda h: (-counts[h], h))[0]


def _best_relations(game, house_name: str) -> Optional[str]:
    house = game.houses[house_name]
    suitors = [n for n in sorted(game.houses)
               if n != house_name and n in game.realms
               and n not in house.at_war_with]
    if not suitors:
        return None
    return max(suitors, key=lambda n: (house.relations.get(n, 0), n))


def _strongest_rival(game, house_name: str) -> Optional[str]:
    rivals = [n for n in sorted(game.houses)
              if n != house_name and n in game.realms]
    if not rivals:
        return None
    return max(rivals, key=lambda n: (_strength(game, n), n))


def _worst_province(game, house_name: str):
    provs = game.provinces_of(house_name)
    if not provs:
        return None
    return max(provs, key=lambda p: (p.unrest, p.pid))


# --- family scoring (pure) ---------------------------------------------------

def _score_family(game, house_name: str, family: str, ruler, realm) -> float:
    """How much THIS ruler wants THIS family, from dispositions + world. Pure."""
    if family == "Conquest":
        s = _disp(ruler, "militarist_pacifist")
        return s + (20.0 if _weakest_neighbor(game, house_name) else -40.0)
    if family == "Dominion":
        s = _disp(ruler, "ambitious_content") + _stat(realm, "industry")
        return s + (10.0 if _found_spot(game, house_name) else 0.0)
    if family == "Buyout":
        s = _stat(realm, "intrigue") + _disp(ruler, "labor_capital")
        return s + (10.0 if _richest_rival(game, house_name) else -40.0)
    if family == "Dynasty":
        s = _disp(ruler, "patient_impulsive")
        return s + (10.0 if _marriageable(realm, ruler) else -40.0)
    if family == "Intrigue":
        return _stat(realm, "intrigue") - _disp(ruler, "honest_deceitful")
    if family == "Glory":
        return _disp(ruler, "ambitious_content") + _disp(ruler, "bold_craven")
    if family == "Consolidation":
        worst = _worst_province(game, house_name)
        unrest = worst.unrest if worst is not None else 0.0
        return _disp(ruler, "paranoid_trusting") + unrest
    return 0.0


def _target_for(game, house_name: str, family: str) -> Optional[str]:
    if family == "Conquest":
        return _weakest_neighbor(game, house_name)
    if family == "Buyout":
        return _richest_rival(game, house_name)
    if family == "Dynasty":
        return _best_relations(game, house_name)
    if family in ("Intrigue", "Glory"):
        return _strongest_rival(game, house_name)
    return None            # Dominion, Consolidation are self-directed


def _why(family: str, target: Optional[str]) -> str:
    at = f" House {target}" if target else ""
    return {
        "Conquest": f"Seeks to break{at or ' a weaker neighbor'} by force",
        "Dominion": "Seeks to industrialize its own lands",
        "Buyout": f"Quietly buying into{at or ' a rival'}'s enterprises",
        "Dynasty": f"Seeks a marriage tie to{at or ' a friendly House'}",
        "Intrigue": f"Working schemes against{at or ' a strong rival'}",
        "Glory": "Chasing prestige and the century's judgment",
        "Consolidation": "Turning inward to settle its own house",
    }[family]


# --- selection & commit (ensure_agenda is the only writer) -------------------

def select_goal(game, house_name: str) -> Optional[Goal]:
    """Deterministic argmax over families (tiebreak: FAMILIES order). No RNG."""
    realm = game.realms.get(house_name)
    if realm is None or realm.ruler is None or not realm.ruler.is_alive:
        return None
    ruler = realm.ruler
    scored = [(-_score_family(game, house_name, fam, ruler, realm), i, fam)
              for i, fam in enumerate(FAMILIES)]
    scored.sort()
    _neg, _i, family = scored[0]
    target = _target_for(game, house_name, family)
    return Goal(family=family, target=target, opened_turn=game.turn,
                commit_turns=COMMIT_TURNS, why=_why(family, target))


def ensure_agenda(game, house_name: str) -> Optional[Goal]:
    """Return the House's live goal, re-selecting when the commit window has
    passed or the current target has vanished. The ONLY writer of game.agendas."""
    cur = game.agendas.get(house_name)
    if cur is not None and game.turn < cur.opened_turn + cur.commit_turns:
        if cur.target is None or cur.target in game.houses:
            return cur
    goal = select_goal(game, house_name)
    if goal is not None:
        game.agendas[house_name] = goal
    return goal


def goal_domain(goal: Goal) -> str:
    return FAMILY_DOMAIN[goal.family]


# --- the signature initiative (ripe & affordable, else None) -----------------

def goal_initiative(game, house_name: str, goal: Goal
                    ) -> Optional[Tuple[str, dict]]:
    """The goal's signature verb + kwargs when it is ripe and affordable, for
    ai._pick_initiative to prefer. Returns None to fall back to disposition
    play (Glory has no signature - it lives purely in petition/directive bias)."""
    house = game.houses[house_name]
    realm = game.realms[house_name]
    fam, target = goal.family, goal.target
    if fam == "Conquest":
        if (target in game.houses and target not in house.at_war_with
                and house.truces.get(target, 0) <= game.turn
                and not house.at_war_with):
            return "declare_war", {"target_house": target}
        return None
    if fam == "Dominion":
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
        return None
    if fam == "Buyout":
        # Try to start a takeover (primary verb — reach it before buy_shares)
        if (target in game.houses and target != house_name
                and not any(t.target_house == target and t.buyer_house == house_name
                            and not t.complete for t in game.takeovers)):
            return "start_takeover", {"target_house": target}
        # Fall back to buying shares to accumulate stake
        if target in game.houses and target != house_name:
            for ent in game.enterprises:
                if ent.house == target:
                    seller_realm = game.realms.get(target)
                    if seller_realm is None:
                        continue
                    for c in seller_realm.characters:
                        if c.is_alive and c.age >= 16 and c.id != seller_realm.ruler.id:
                            return "buy_shares", {"eid": ent.eid, "seller_id": c.id, "pct": 5.0}
                    break
        return None
    if fam == "Dynasty":
        if (target in game.houses and _marriageable(realm, realm.ruler)
                and not _has_marriage_tie(game, house_name, target)):
            return "propose_marriage", {"target_house": target}
        return None
    if fam == "Intrigue":
        trealm = game.realms.get(target)
        if (trealm is not None and trealm.ruler is not None
                and trealm.ruler.is_alive and _stat(realm, "intrigue") > 0
                and not game.scheme_mgr.scheming(realm.ruler)):
            return "start_scheme", {"target": trealm.ruler,
                                    "scheme_type": "assassination",
                                    "target_house": target}
        return None
    if fam == "Consolidation":
        # Sell shares to raise gold when treasury is low
        if house.treasury < 100:
            for ent in game.enterprises:
                if ent.house == house_name:
                    for rival_name in game.realms:
                        if rival_name == house_name:
                            continue
                        rival_realm = game.realms.get(rival_name)
                        if rival_realm is None:
                            continue
                        for buyer in rival_realm.characters:
                            if buyer.is_alive and buyer.age >= 16:
                                return "sell_shares", {"eid": ent.eid, "buyer_id": buyer.id, "pct": 5.0}
                    break
        worst = _worst_province(game, house_name)
        if worst is not None and worst.unrest > 0:
            return "tour_province", {"province_pid": worst.pid}
        return None
    return None            # Glory: petition/directive bias only
