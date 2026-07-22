"""Relationships that bite: rivals, grievances, plots (mission G11).

Ported from root relationships.py onto realms dicts and a SchemeManager
parameter. Every player-civ special case is gone - all houses run the same
logic. The opinion matrix stays module state (it lives in
gilded.society.characters); get_state()/set_state() snapshot it and the
last-ruler memory for saves."""

from typing import List

from gilded.society.characters import opinion_matrix
from gilded.society.characters import modify_opinion as _modify_opinion
from gilded.society.dispositions import apply_drift

RIVAL_AT = -25
FRIEND_AT = 25
GRIEVANCE_CHANCE = 0.05
AMBITIOUS_GRIEVANCE_CHANCE = 0.15
PLOT_CHANCE = 0.06
FOREIGN_PLOT_CHANCE = 0.03
MAX_MESSAGES = 4

_last_rulers = {}


def opinion_of(a, b) -> int:
    return opinion_matrix.get((a.id, b.id), 0)


def modify_opinion(a, b, delta, reason: str = "") -> None:
    _modify_opinion(a, b, delta, reason)


def get_relation(a, b) -> str:
    o = opinion_of(a, b)
    if o <= RIVAL_AT:
        return "rival"
    if o >= FRIEND_AT:
        return "friend"
    return "neutral"


def tick_relationships(realms, scheme_mgr, turn, rng) -> List[str]:
    """Grievances, plots, and secret discovery for every realm."""
    msgs: List[str] = []
    for house, realm in realms.items():
        msgs.extend(_succession_grievances(house, realm, rng))
        msgs.extend(_grievances(realm, rng))
        msgs.extend(_discover_secrets(realm, rng))
        msgs.extend(_maybe_start_plot(realms, house, realm, scheme_mgr, rng))
    if len(msgs) > MAX_MESSAGES:
        msgs = rng.sample(msgs, MAX_MESSAGES)
    return msgs


def _succession_grievances(house, realm, rng) -> List[str]:
    """Passed-over kin resent the new ruler - the classic source of rivals."""
    msgs = []
    ruler = realm.ruler
    last = _last_rulers.get(house)
    _last_rulers[house] = ruler.id
    if last is None or last == ruler.id or not ruler.is_alive:
        return msgs
    for c in realm.dynasty.all_characters.values():
        if not c.is_alive or c.age < 16 or c.id == ruler.id:
            continue
        was_rival = get_relation(c, ruler) == "rival"
        modify_opinion(c, ruler, -rng.randint(15, 30), "passed over")
        # Being passed over marks a person for life (spec 3.4 drift).
        for pk, amt in (("forgiving_vengeful", 12.0), ("ambitious_content", -8.0)):
            d = apply_drift(c, pk, amt, "passed over")
            if d:
                msgs.append(d)
        if not was_rival and get_relation(c, ruler) == "rival":
            msgs.append(f"{c.name} has become a rival of {ruler.name}")
    return msgs


def _grievances(realm, rng) -> List[str]:
    msgs = []
    ruler = realm.ruler
    if not ruler.is_alive:
        return msgs
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.id == ruler.id:
            continue
        ambitious = "Cunning" in c.traits or "Opportunistic" in c.traits or c.stress > 100
        chance = AMBITIOUS_GRIEVANCE_CHANCE if ambitious else GRIEVANCE_CHANCE
        if rng.random() < chance:
            was_rival = get_relation(c, ruler) == "rival"
            modify_opinion(c, ruler, -rng.randint(5, 12), "ambition")
            if not was_rival and get_relation(c, ruler) == "rival":
                msgs.append(f"{c.name} has become a rival of {ruler.name}")
    return msgs


def _discover_secrets(realm, rng) -> List[str]:
    """Spec 3.5: courtiers sniff out the realm's secrets; discovery chance
    scales with the observer's Intrigue (1% per point per turn, cap 30%)."""
    msgs: List[str] = []
    observers = [c for c in realm.court.positions.values()
                 if c is not None and c.is_alive]
    ruler = realm.ruler
    if ruler is not None and ruler.is_alive and ruler not in observers:
        observers.append(ruler)
    subjects = list(observers)
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c not in subjects:
            subjects.append(c)
    for subject in subjects:
        for secret in subject.secrets:
            for obs in observers:
                if obs.id == subject.id or secret.is_known_by(obs.id):
                    continue
                chance = min(0.3, obs.get_effective_stat("intrigue") * 0.01)
                if rng.random() < chance:
                    secret.holders.add(obs.id)
                    msgs.append(f"{obs.name} has uncovered a secret: "
                                f"{secret.description}")
    return msgs


def _maybe_start_plot(realms, house, realm, scheme_mgr, rng) -> List[str]:
    msgs = []
    ruler = realm.ruler
    if not ruler.is_alive:
        return msgs
    court_ids = {c.id for c in realm.court.positions.values() if c}
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.id == ruler.id or scheme_mgr.scheming(c):
            continue
        if get_relation(c, ruler) == "rival" and rng.random() < PLOT_CHANCE:
            scheme_type = "coup" if c.id in court_ids else "assassination"
            scheme = scheme_mgr.start_scheme(c, ruler, scheme_type, house)
            for ally in realm.characters:
                if ally.is_alive and ally.id not in (c.id, ruler.id) and get_relation(ally, ruler) == "rival":
                    scheme.add_participant(ally)
            msgs.append(f"Whispers in {house}: someone moves against {ruler.name}")
            break
    if not scheme_mgr.scheming(ruler):
        targets = [(n, r.ruler) for n, r in realms.items()
                   if n != house and r.ruler is not None and r.ruler.is_alive
                   and get_relation(ruler, r.ruler) == "rival"]
        if targets and rng.random() < FOREIGN_PLOT_CHANCE:
            n, t = rng.choice(targets)
            scheme_mgr.start_scheme(ruler, t, "assassination", n)
            msgs.append(f"Agents of {house} slip across the border...")
    return msgs


def get_state() -> dict:
    """Snapshot the module-level relationship state for saves."""
    return {"opinions": dict(opinion_matrix), "last_rulers": dict(_last_rulers)}


def set_state(state: dict) -> None:
    """Restore the module-level relationship state from a save."""
    opinion_matrix.clear()
    opinion_matrix.update(state.get("opinions", {}))
    _last_rulers.clear()
    _last_rulers.update(state.get("last_rulers", {}))