"""World facts (Gilded Saga section 1): durable typed statements the story reads.

A WorldFact persists for the whole century, distinct from a transient
TurnEvent (one turn's display text). facts_from_turn() derives the turn's
facts from the already-resolved sim record - pure, deterministic, no state
mutation, no randomness."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WorldFact:
    turn: int
    subject_kind: str          # "house" | "province" | "character" | "world"
    subject_id: str            # house name | str(pid) | character id | ""
    predicate: str             # canonical verb
    object: str = ""
    magnitude: float = 0.0


class FactStore:
    """Append-only, indexed for predicate evaluation."""

    def __init__(self) -> None:
        self.facts: List[WorldFact] = []
        self._by_subject: Dict[Tuple[str, str], List[WorldFact]] = {}
        self._by_predicate: Dict[str, List[WorldFact]] = {}

    def add(self, fact: WorldFact) -> None:
        self.facts.append(fact)
        self._by_subject.setdefault((fact.subject_kind, fact.subject_id), []).append(fact)
        self._by_predicate.setdefault(fact.predicate, []).append(fact)

    def _matches(self, predicate, subject, object, since_turn) -> List[WorldFact]:
        pool = self._by_predicate.get(predicate, [])
        out = []
        for f in pool:
            if subject is not None and (f.subject_kind, f.subject_id) != subject:
                continue
            if object is not None and f.object != object:
                continue
            if since_turn is not None and f.turn < since_turn:
                continue
            out.append(f)
        return out

    def exists(self, predicate: str, *, subject: Optional[Tuple[str, str]] = None,
               object: Optional[str] = None, since_turn: Optional[int] = None) -> bool:
        return len(self._matches(predicate, subject, object, since_turn)) > 0

    def count(self, predicate: str, *, subject: Optional[Tuple[str, str]] = None,
              object: Optional[str] = None, since_turn: Optional[int] = None) -> int:
        return len(self._matches(predicate, subject, object, since_turn))


def _empty_snapshot() -> Dict:
    return {"war": {}, "atrocity": {}, "fallen": {}, "ruler": {}, "phase": ""}


def facts_from_turn(game, prev: Optional[Dict] = None):
    """Pure: derive this turn's WorldFacts by diffing resolved state against
    the previous snapshot. Returns (facts, new_snapshot). No mutation, no rng."""
    if prev is None:
        prev = _empty_snapshot()
    turn = game.turn
    facts: List[WorldFact] = []

    # wars: new entries in each house's at_war_with vs last snapshot
    war_prev = prev.get("war", {})
    war_now: Dict[str, set] = {}
    for name in sorted(game.houses):
        now = set(getattr(game.houses[name], "at_war_with", set()))
        war_now[name] = now
        for target in sorted(now - set(war_prev.get(name, set()))):
            facts.append(WorldFact(turn, "house", name, "went_to_war", object=target))
        for target in sorted(set(war_prev.get(name, set())) - now):
            facts.append(WorldFact(turn, "house", name, "made_peace", object=target))

    # atrocities: house_atrocities delta
    atr_prev = prev.get("atrocity", {})
    atr_now = dict(getattr(game.tide, "house_atrocities", {}))
    for name in sorted(atr_now):
        delta = atr_now[name] - atr_prev.get(name, 0.0)
        if delta > 0.0:
            facts.append(WorldFact(turn, "house", name, "committed_atrocity",
                                   magnitude=delta))

    # fallen: revolution / transformed newly set
    fallen_prev = prev.get("fallen", {})
    fallen_now = dict(getattr(game, "fallen", {}))
    for name in sorted(fallen_now):
        if name not in fallen_prev:
            pred = "transformed" if fallen_now[name] == "transformed" else "suffered_revolution"
            facts.append(WorldFact(turn, "house", name, pred))

    # rulers: succession this turn
    ruler_prev = prev.get("ruler", {})
    ruler_now: Dict[str, str] = {}
    for name in sorted(getattr(game, "realms", {})):
        realm = game.realms[name]
        ruler = getattr(realm, "ruler", None)
        rid = getattr(ruler, "id", "") if ruler is not None else ""
        ruler_now[name] = rid
        if name in ruler_prev and ruler_prev[name] and rid and rid != ruler_prev[name]:
            facts.append(WorldFact(turn, "house", name, "lost_ruler", object=rid))

    # tide phase change (world)
    phase_prev = prev.get("phase", "")
    phase_now = game.tide.phase()
    if phase_now != phase_prev:
        facts.append(WorldFact(turn, "world", "", "reached_tide_phase", object=phase_now))

    snapshot = {"war": war_now, "atrocity": atr_now, "fallen": fallen_now,
                "ruler": ruler_now, "phase": phase_now}
    return facts, snapshot