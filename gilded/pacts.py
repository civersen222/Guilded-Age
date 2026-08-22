"""Standing pacts of alliance.

A marriage's blood ties can seal a pact between two Houses. Unlike the raw
relation bonus a wedding grants, a pact is a binding commitment: while it
stands, neither House may declare war on the other, the AI war-target pickers
refuse to name an allied House, and when one side is attacked the other is
called to arms and must either join the war within a few turns or record a
refusal in the world log.

Pacts are scarce. There is a hard cap on how many stand at once and on how
many any single House may hold, so a wedding is only one path to a pact and
not every wedding produces one.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


MAX_PACTS = 8
MAX_PACTS_PER_HOUSE = 2
CALL_TO_ARMS_DEADLINE = 3


@dataclass
class Pact:
    house_a: str
    house_b: str
    formed_turn: int = 0


def _pact_objects(game) -> List[Pact]:
    """The underlying Pact records, in formation order."""
    return list(getattr(game, "pacts", []))


def standing_pacts(game) -> Set[frozenset]:
    """The House pairs that currently hold a pact, as a set of frozensets."""
    return {frozenset((p.house_a, p.house_b)) for p in _pact_objects(game)}


def _pact_between(game, house_a: str, house_b: str) -> Optional[Pact]:
    for pact in _pact_objects(game):
        if {pact.house_a, pact.house_b} == {house_a, house_b}:
            return pact
    return None


def allies_of(game, house_name: str) -> Set[str]:
    """The Houses bound to house_name by a standing pact."""
    out: Set[str] = set()
    for pair in standing_pacts(game):
        if house_name in pair:
            out.update(pair - {house_name})
    return out


def _count_for(game, house_name: str) -> int:
    return sum(1 for pair in standing_pacts(game) if house_name in pair)


def are_allies(game, house_a: str, house_b: str) -> bool:
    """Whether a standing pact binds the two Houses."""
    return _pact_between(game, house_a, house_b) is not None


def form_pact(game, house_a: str, house_b: str) -> Optional[str]:
    """Seal a pact between two Houses, respecting the scarcity caps.

    Returns a gazette message on success, or None when the pact could not be
    formed (unknown House, already allied, or the standing/per-House caps
    reached)."""
    if house_a not in game.houses or house_b not in game.houses:
        return None
    if house_a == house_b:
        return None
    if _pact_between(game, house_a, house_b) is not None:
        return None
    if len(standing_pacts(game)) >= MAX_PACTS:
        return None
    if _count_for(game, house_a) >= MAX_PACTS_PER_HOUSE:
        return None
    if _count_for(game, house_b) >= MAX_PACTS_PER_HOUSE:
        return None
    game.pacts.append(Pact(house_a, house_b, game.turn))
    return f"House {house_a} and House {house_b} seal a pact of alliance"


def may_declare_war(game, house: str, target: str) -> bool:
    """Whether house may declare war on target.

    False when the two are already at war, bound by a standing pact, or under
    a truce that has not yet expired."""
    house_obj = game.houses[house]
    if target in house_obj.at_war_with:
        return False
    if _pact_between(game, house, target) is not None:
        return False
    if house_obj.truces.get(target, 0) > game.turn:
        return False
    return True


def call_to_arms(game, war) -> List[str]:
    """When a war opens, every allied House of the defender is pledged to
    answer. The pledge is recorded so the pact tick resolves it within
    CALL_TO_ARMS_DEADLINE turns."""
    msgs: List[str] = []
    seen = getattr(game, "pact_seen_wars", None)
    if seen is None:
        seen = game.pact_seen_wars = set()
    if id(war) in seen:
        return msgs
    seen.add(id(war))
    for ally in sorted(allies_of(game, war.defender)):
        if ally in game.houses[war.defender].at_war_with:
            continue
        if ally in game.houses[war.aggressor].at_war_with:
            continue                   # already engaged against the aggressor
        if _pact_between(game, ally, war.aggressor) is not None:
            msgs.append(f"House {ally} cannot turn its arms on its own ally "
                        f"House {war.aggressor}")
            continue
        game.pact_pledges[ally] = (war, game.turn + CALL_TO_ARMS_DEADLINE)
        msgs.append(f"House {war.defender} calls House {ally} to arms against "
                    f"House {war.aggressor}")
    return msgs


def pact_tick(game) -> List[str]:
    """One turn of pact life: new blood ties seal pacts, pending calls to
    arms are answered or refused.

    A pledged House either joins its ally's war or records a refusal in the
    log naming both it and the aggressor it declined to face."""
    msgs: List[str] = []
    marriages = getattr(game, "marriages", MarriageView()).marriages
    contracts = getattr(game, "marriages", MarriageView()).contracts
    seen_pairs: set = set()
    for ca, ha, cb, hb in marriages:
        if ha == hb:
            continue
        # The FOUNDBING marriage of a pair is its earliest one (marriages is
        # chronological). A pact is SCARCE: it seals only when that founding
        # bond carries a BOARD SEAT — a founding political alliance, not a
        # later renewal wedding. This keeps pacts a handful per century rather
        # than the majority of pairs, and leaves houses whose first wedding was
        # a plain alliance free to make war.
        pair_key = (ha, hb) if ha < hb else (hb, ha)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        ckey = (ca, cb) if (ca, cb) in contracts else (cb, ca)
        contract = contracts.get(ckey)
        if contract is None or not contract.board_seat:
            continue
        msg = form_pact(game, ha, hb)
        if msg:
            msgs.append(msg)
    # A war can open by any path (a docket motion, a constructed test world) -
    # the call to arms must not depend on the opener having wired
    # call_to_arms: any war that stands but has never been seen by the pact
    # tick gets its defenders' allies pledged here.
    seen = getattr(game, "pact_seen_wars", None)
    if seen is None:
        seen = game.pact_seen_wars = set()
    for war in list(game.wars):
        msgs.extend(call_to_arms(game, war))
    for house in sorted(list(game.pact_pledges)):
        war, deadline = game.pact_pledges[house]
        if war not in game.wars:
            del game.pact_pledges[house]
            continue
        if house in (war.aggressor, war.defender) or house in war.allies:
            del game.pact_pledges[house]
            continue
        busy = any(house in (o.aggressor, o.defender) or house in o.allies
                   for o in game.wars if o is not war)
        pacted = _pact_between(game, house, war.aggressor) is not None
        if busy or pacted or game.turn > deadline:
            del game.pact_pledges[house]
            if pacted:
                msgs.append(f"House {house} cannot turn its arms on its own "
                            f"ally House {war.aggressor}")
            else:
                msgs.append(f"House {house} refuses House {war.defender}'s "
                            f"call against House {war.aggressor}")
            continue
        war.allies.append(house)
        game.houses[house].at_war_with.add(war.aggressor)
        game.houses[war.aggressor].at_war_with.add(house)
        del game.pact_pledges[house]
        msgs.append(f"House {house} answers the call to arms and joins House "
                    f"{war.defender} against House {war.aggressor}")
    return msgs


class MarriageView:
    """Empty stand-in so pact_tick works on a game without a registry."""

    def __init__(self):
        self.marriages: List[tuple] = []
        self.contracts: Dict[tuple, object] = {}
