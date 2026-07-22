"""Beats & predicates (Gilded Saga section 2): the spine language.

A Predicate composes over the FactStore, turn clock, and tide level; an
`@self` subject_id resolves against the beat's bound cast at eval time. A
Beat is a named, two-tier story unit: load-bearing beats advance only via a
satisfied completion predicate; soft beats gate nothing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gilded.saga.facts import FactStore


@dataclass
class Predicate:
    kind: str                      # fact_exists|turn_reached|tide_reached|all|any
    predicate: str = ""
    subject_kind: str = ""
    subject_id: str = ""           # may be "@self"
    object: str = ""
    min_count: int = 1
    turn: int = 0
    level: float = 0.0
    parts: List["Predicate"] = field(default_factory=list)


def eval_predicate(pred: Predicate, facts: FactStore, game,
                   cast: Optional[Dict[str, str]] = None) -> bool:
    cast = cast or {}
    if pred.kind == "fact_exists":
        subject = None
        if pred.subject_kind:
            sid = pred.subject_id
            if sid.startswith("@"):
                sid = cast.get(sid[1:], "\0")     # unbound -> never matches
            subject = (pred.subject_kind, sid)
        object = pred.object or None
        return facts.count(pred.predicate, subject=subject, object=object) >= pred.min_count
    if pred.kind == "turn_reached":
        return game.turn >= pred.turn
    if pred.kind == "tide_reached":
        return game.tide.level >= pred.level
    if pred.kind == "all":
        return all(eval_predicate(p, facts, game, cast) for p in pred.parts)
    if pred.kind == "any":
        return any(eval_predicate(p, facts, game, cast) for p in pred.parts)
    return False


@dataclass
class Beat:
    bid: str
    source: str                    # "age" | "rival" | "chronicle"
    title: str
    load_bearing: bool
    completion: Optional[Predicate] = None
    foreshadow: str = ""
    payoff: str = ""
    cast: Dict[str, str] = field(default_factory=dict)
    state: str = "pending"         # pending | active | complete
    opened_turn: int = 0
    closed_turn: int = 0
    next_bids: List[str] = field(default_factory=list)