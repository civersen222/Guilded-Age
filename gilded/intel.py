"""Earned intel (Stage 2): what one House can legibly SEE of another's
GOAL, as a tier-0..3 fog the viewer earns. report() is a PURE read-model -
it never mutates the game (soak-tested like the dashboard). The only WRITE
in the fog system is the informant lever, and that lives in docket as an
honest initiative (establish_informant) costing one attention.

Tiers are ADDITIVE (spec 2.3): each earned source contributes one step, and
the tier is the count, capped at 3.
  Tier 0 Blind   - name & rank only.
  Tier 1 Mood    - a shared border: you can read the border mood.
  Tier 2 Intent  - a marriage tie or standing relations: the goal family.
  Tier 3 Depth   - a secret you hold on their ruler, or a spymaster edge, or
                   a placed informant: the family AND its target."""

from dataclasses import dataclass
from typing import List, Optional

from gilded.fronts import REGIMENT_POP_COST


@dataclass(frozen=True)
class IntelReport:
    tier: int
    breakdown: List[str]
    apparent_intent: str


def _strength(game, house_name: str) -> float:
    pop = sum(p.population for p in game.provinces_of(house_name))
    return pop // REGIMENT_POP_COST + game.houses[house_name].treasury


def _shares_border(game, viewer: str, target: str) -> bool:
    owned = {p.pid for p in game.provinces_of(viewer)}
    for p in game.provinces_of(target):
        if p.neighbors & owned:
            return True
    return False


def _has_marriage_tie(game, viewer: str, target: str) -> bool:
    for tie in getattr(game.marriages, "marriages", []):
        # tie is the bare 4-tuple (char_a, house_a, char_b, house_b)
         if len(tie) >= 4 and {tie[1], tie[3]} == {viewer, target}:
            return True
    return False


def _diplomatic_visibility(game, viewer: str, target: str) -> bool:
    if _has_marriage_tie(game, viewer, target):
        return True
    return game.houses[viewer].relations.get(target, 0) != 0


def _court_intrigue(game, house: str) -> float:
    realm = game.realms.get(house)
    if realm is None:
        return 0.0
    return max((c.get_effective_stat("intrigue")
                for c in realm.court.positions.values()
                if c and c.is_alive), default=0.0)


def _depth_visibility(game, viewer: str, target: str) -> bool:
    trealm = game.realms.get(target)
    vrealm = game.realms.get(viewer)
    if trealm is None or vrealm is None or trealm.ruler is None:
        return False
    viewer_ids = {c.id for c in vrealm.dynasty.all_characters.values()}
    if any(viewer_ids & s.holders for s in trealm.ruler.secrets):
        return True
    return _court_intrigue(game, viewer) > _court_intrigue(game, target)


def _mood(game, viewer: str, target: str) -> str:
    rel = game.houses[viewer].relations.get(target, 0)
    if rel < 0:
        return "The mood at their court runs cold toward you"
    if rel > 0:
        return "The mood at their court runs warm toward you"
    return "Their court gives little away"


def report(game, viewer: str, target: str) -> IntelReport:
    """Pure: what `viewer` can legibly read of `target`'s agenda."""
    sources: List[str] = []
    if _shares_border(game, viewer, target):
        sources.append("shared border")
    if _diplomatic_visibility(game, viewer, target):
        sources.append("diplomatic ties")
    if _depth_visibility(game, viewer, target):
        sources.append("intelligence assets")
    if (viewer, target) in game.informants:
        sources.append("informant in place")
    tier = min(3, len(sources))

    goal = game.agendas.get(target)
    if tier <= 0 or goal is None:
        intent = "Their intentions are unknown"
    elif tier == 1:
        intent = _mood(game, viewer, target)
    elif tier == 2:
        intent = f"Pursuing {goal.family}"
    else:
        at = f" against House {goal.target}" if goal.target else ""
        intent = f"Pursuing {goal.family}{at}: {goal.why}"
    return IntelReport(tier=tier, breakdown=sources, apparent_intent=intent)


def threat_rank(game) -> List[str]:
    """Deterministic ordering of every OTHER House by danger to the player: a
    House whose agenda targets the player ranks first, then by raw strength.
    Pure - orders the Powers roster."""
    player = next((h for h in game.houses if game.houses[h].is_player), None)
    others = [h for h in sorted(game.houses) if h != player]

    def key(h: str):
        goal = game.agendas.get(h)
        aims = 1 if (goal is not None and goal.target == player) else 0
        return (-aims, -_strength(game, h), h)

    return sorted(others, key=key)
