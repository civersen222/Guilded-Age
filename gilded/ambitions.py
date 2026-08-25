"""Mission C2 - the player has a stake: a House ambition and the court's
private wants.

`ambitions.set_ambition(house, family, target)` records a Goal on
`game.agendas` - the SAME goal the AI houses carry - so every C1 reader
(intel.report, threat_rank, the AI's soft bias) sees the player's stake
without a single special case. The AI never writes `game.agendas` for a
house that already has a goal, so a player-set stake is never clobbered.

Each ADULT member of the House (age >= 16) then carries a private WANT -
a stance toward the ambition COMPUTED from their own dispositions, never
drawn from the RNG, so the court backs or opposes the ruler's stake for
personal reasons and two boots of one seed see the identical court.

At the close of the commit window (10 turns) the ambition RESOLVES: the
win condition - movement on the family's natural axis measured against the
snapshot taken at the moment the stake was set - either pays a journal
entry labelled "ambition" (ladder movement on the capital axis) or the
stake falls short. The resolution is a consequence beat, so the
broadsheet shows the stake landing.

Deterministic: no RNG anywhere in this module.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from gilded.agenda import COMMIT_TURNS, FAMILIES, Goal
from gilded.beats import Beat

AMBITION_REWARD = 300.0       # a fulfilled ambition pays the treasury
STANCE_BACKS_AT = 15.0        # disposition this far for the ambition: backs
STANCE_OPPOSES_AT = -15.0     # this far against: opposes; in between: wary

# family -> (the disposition that reads the stance, "backs" polarity)
# +1 means a positive value backs the ambition; -1 flips it.
FAMILY_DISPOSITION = {
    "Conquest": ("militarist_pacifist", 1.0),
    "Dominion": ("ambitious_content", 1.0),
    "Buyout": ("generous_greedy", 1.0),
    "Dynasty": ("traditionalist_modernist", 1.0),
    "Intrigue": ("honest_deceitful", -1.0),   # the deceitful side backs it
    "Glory": ("bold_craven", 1.0),
    "Consolidation": ("cruel_compassionate", 1.0),
}

# family -> families that carry a named rival target
TARGETED_FAMILIES = frozenset({"Conquest", "Buyout", "Intrigue", "Dynasty"})

# stance -> the private want, by name, for the family's stake
WANT_TEXT = {
    "backs": {
        "Conquest": "presses for war on the frontier",
        "Dominion": "pushes for new provinces",
        "Buyout": "hunts for rival shares",
        "Dynasty": "plans marriages that bind the line",
        "Intrigue": "keeps ears in other courts",
        "Glory": "collects trophies and titles",
        "Consolidation": "keeps the mills quiet",
    },
    "wary": {
        "Conquest": "watches the frontier, undecided",
        "Dominion": "hesitates at the borders",
        "Buyout": "watches the share prices",
        "Dynasty": "watches the succession talk",
        "Intrigue": "keeps their own letters safe",
        "Glory": "lets others take the glory",
        "Consolidation": "waits to see the labor question",
    },
    "opposes": {
        "Conquest": "quietly undermines the war effort",
        "Dominion": "resists paying for new borders",
        "Buyout": "holds their own shares close",
        "Dynasty": "plots against the line",
        "Intrigue": "feeds the rivals whispers",
        "Glory": "spits on the ruler's name",
        "Consolidation": "loosens the screws on the mills",
    },
}


def _rivals(game, house_name: str) -> List[str]:
    """The House's rivals: houses it is at war with, then the rest,
    each sorted by name - the first is the default target."""
    house = game.houses[house_name]
    at_war = [h for h in sorted(game.houses)
              if h != house_name and h in house.at_war_with]
    rest = [h for h in sorted(game.houses)
            if h != house_name and h not in house.at_war_with]
    return at_war + rest


def _intel_tier(game, viewer: str, target: str) -> int:
    from gilded.intel import report
    return report(game, viewer, target).tier


def _snapshot(game, house_name: str, target: Optional[str]) -> dict:
    """The state the ambition is measured against - taken the turn the
    stake is set."""
    provs = game.provinces_of(house_name)
    mean_unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
    rel = game.houses[house_name].relations
    mean_rel = (sum(rel.values()) / len(rel)) if rel else 0.0
    # the quietest rival's mills - Consolidation wins by standing quieter
    # than every rival (an honest relative axis: the labor directive
    # calms the player's own mills, rivalry unrest is the world's own)
    return {
        "provinces": len(provs),
        "enterprises": len([e for e in game.enterprises
                            if e.house == house_name]),
        "treasury": game.houses[house_name].treasury,
        "mean_unrest": mean_unrest,
        "mean_rel": mean_rel,
        "rel_with_target": (game.houses[target].relations.get(house_name, 0)
                            if target else 0),
        "informed": _intel_tier(game, house_name, target) if target else 0,
        "war_with_target": bool(target)
        and target in game.houses[house_name].at_war_with,
    }


def _fulfilled(game, house_name: str, goal: Goal, snap: dict) -> bool:
    """The win condition: real movement on the family's natural axis
    since the snapshot. Every condition is a real win - none is certain."""
    from gilded.intel import report
    family = goal.family
    if family == "Conquest":
        return (len(game.provinces_of(house_name)) > snap["provinces"]
                and snap["war_with_target"])
    if family == "Dominion":
        return len(game.provinces_of(house_name)) > snap["provinces"]
    if family == "Buyout":
        if goal.target is None:
            return False
        # the target's regard for this House - the docket's own lever
        # (envoys, marriages, treaties) is what moves it
        return (game.houses[goal.target].relations.get(house_name, 0)
                > snap["rel_with_target"])
    if family == "Dynasty":
        rel = game.houses[house_name].relations
        now = (sum(rel.values()) / len(rel)) if rel else 0.0
        return now > snap["mean_rel"]
    if family == "Intrigue":
        return (goal.target is not None
                and report(game, house_name, goal.target).tier
                > snap["informed"])
    if family == "Glory":
        return (len(game.provinces_of(house_name)) > snap["provinces"]
                or game.houses[house_name].treasury > snap["treasury"])
    if family == "Consolidation":
        # the quietest mills in the realm: standing quieter than every
        # rival at the close. The labor directive is the player's lever;
        # the world's own unrest decides who else is quiet.
        provs = game.provinces_of(house_name)
        if not provs:
            return False
        now = sum(p.unrest for p in provs) / len(provs)
        rival_mus = [sum(p.unrest for p in game.provinces_of(h))
                     / len(game.provinces_of(h))
                     for h in game.houses
                     if h != house_name and game.provinces_of(h)]
        return bool(rival_mus) and now < min(rival_mus)
    return False


# --- the public facade ------------------------------------------------------

class AmbitionsFacade:
    """`game.ambitions` - set the stake, read it, read the court.

    - `.set_ambition(house, family, target=None)`: the player's stake
    - `.status(house)`: the banner's data - family, target, turns_left,
      fulfilled, why
    - `.wants(house)`: every adult's private want + stance
    - `.resolve_due()`: called by end_turn - resolves whose window has
      closed, pays the fulfilled ones, and logs the beats
    """

    def __init__(self, game):
        self.game = game
        # house -> the snapshot the ambition is measured against
        self._start: Dict[str, dict] = {}
        # house -> fulfilled? once the window closes
        self._resolved: Dict[str, bool] = {}

    # --- the stake ----------------------------------------------------------

    def set_ambition(self, house_name: str, family: str,
                     target: Optional[str] = None):
        """Record the House's stake. The ONLY writer of a player ambition;
        the AI never overwrites a house whose goal it did not choose."""
        game = self.game
        if family not in FAMILIES:
            raise ValueError(f"unknown family: {family}")
        if target is None and family in TARGETED_FAMILIES:
            rivals = _rivals(game, house_name)
            target = rivals[0] if rivals else None
        why = {
            "Conquest": f"House {target} must bend",
            "Dominion": "the borders are too small",
            "Buyout": f"House {target}'s shares are for the taking",
            "Dynasty": f"the line must bind House {target}",
            "Intrigue": f"House {target}'s secrets are worth having",
            "Glory": "a name remembered past the century",
            "Consolidation": "the mills must stand quiet",
        }[family]
        goal = Goal(family=family, target=target, opened_turn=game.turn,
                    commit_turns=COMMIT_TURNS, why=why)
        game.agendas[house_name] = goal
        self._start[house_name] = _snapshot(game, house_name, target)
        self._resolved.pop(house_name, None)
        self.wants(house_name)  # every adult carries their private want
        beat = Beat(
            turn=game.turn, kind="signature", house=house_name,
            text=(f"House {house_name} sets its ambition: {family}"
                  + (f" against House {target}" if target else "")
                  + f" - {why}"),
            source="ambitions.set_ambition", causes=(),
            face=game.realms[house_name].ruler.name, facet="ambition",
        )
        game.beats.append(beat)
        return goal

    # --- the read model -----------------------------------------------------

    def status(self, house_name: str) -> dict:
        """The banner's data. turns_left counts down from the commit
        window; fulfilled stays None until the window closes; clock is
        the banner's own words - "turn 1 of 10" the turn the stake is
        set, "turn 4 of 10" after three end_turns."""
        game = self.game
        goal = game.agendas.get(house_name)
        if goal is None:
            return {"family": None, "target": None, "turns_left": 0,
                    "progress": 0.0,
                    "fulfilled": None, "why": None, "started_turn": None,
                    "clock": None}
        elapsed = game.turn - goal.opened_turn
        current = min(goal.commit_turns, max(1, elapsed + 1))
        clock = f"turn {current} of {goal.commit_turns}"
        progress = min(1.0, max(0.0, elapsed / goal.commit_turns))
        if elapsed >= goal.commit_turns:
            return {"family": goal.family, "target": goal.target,
                    "turns_left": 0, "progress": 1.0,
                    "fulfilled": self._resolved.get(house_name),
                    "why": goal.why, "started_turn": goal.opened_turn,
                    "clock": clock}
        return {"family": goal.family, "target": goal.target,
                "turns_left": goal.commit_turns - elapsed,
                "progress": progress,
                "fulfilled": None, "why": goal.why,
                "started_turn": goal.opened_turn, "clock": clock}

    def wants(self, house_name: str) -> List[dict]:
        """Every adult's private want: the stance COMPUTED from their
        own disposition on the family's line, the want text by name, and
        the disposition the stance was computed from."""
        game = self.game
        goal = game.agendas.get(house_name)
        realm = game.realms.get(house_name)
        if goal is None or realm is None:
            return []
        key, polarity = FAMILY_DISPOSITION[goal.family]
        out: List[dict] = []
        for c in sorted(realm.characters, key=lambda c: c.id):
            if c.age < 16:
                continue
            value = float(c.dispositions.get(key, 0.0)) * polarity
            if value > STANCE_BACKS_AT:
                stance = "backs"
            elif value < STANCE_OPPOSES_AT:
                stance = "opposes"
            else:
                stance = "wary"
            text = f"{c.name} {WANT_TEXT[stance][goal.family]}"
            # the model carries its own want - the court reads from here
            c.want = {"text": text, "disposition": key, "stance": stance}
            out.append({
                "id": c.id,
                "name": c.name,
                "age": c.age,
                "traits": list(c.traits),
                "stance": stance,
                "disposition": key,
                "value": value,
                "text": text,
            })
        return out

    def cards(self, house_name: str) -> List[dict]:
        """The House tab's court cards: the SAME data as `.wants`, named
        for the view layer (want_text instead of text)."""
        out = []
        for w in self.wants(house_name):
            card = dict(w)
            card["want_text"] = card.pop("text")
            out.append(card)
        return out

    # --- the resolution -----------------------------------------------------

    def resolve_due(self, house_name: str) -> Optional[dict]:
        """Resolve this house's ambition if its window has closed this
        turn. Pays the treasury, logs a consequence beat labelled
        'ambition', and returns the outcome (or None if not yet due)."""
        game = self.game
        goal = game.agendas.get(house_name)
        if goal is None:
            return None
        # the window closes at the END of the commit_turns-th turn: the
        # chassis resolves before it increments the turn, so the last
        # in-window close is the turn where elapsed == commit_turns - 1
        if game.turn - goal.opened_turn < goal.commit_turns - 1:
            return None
        if house_name not in self._start:
            return None    # an AI-chosen goal, not a player stake
        if house_name in self._resolved:
            return None
        snap = self._start[house_name]
        won = _fulfilled(game, house_name, goal, snap)
        self._resolved[house_name] = won
        if won:
            game.houses[house_name].credit(game.turn, "ambition",
                                           AMBITION_REWARD)
            text = (f"The {goal.family} ambition of House {house_name}"
                    + (f" against House {goal.target}" if goal.target
                       else "")
                    + f" is fulfilled - {AMBITION_REWARD:.0f} gold to the"
                    " treasury")
        else:
            text = (f"The {goal.family} ambition of House {house_name}"
                    + (f" against House {goal.target}" if goal.target
                       else "")
                    + " falls short - the court looks away")
        beat = Beat(
            turn=game.turn, kind="consequence", house=house_name,
            text=text, source="ambitions.resolve_due", causes=(goal.family,),
            face=game.realms[house_name].ruler.name, facet="ambition",
        )
        game.beats.append(beat)
        return {"house": house_name, "family": goal.family,
                "target": goal.target, "fulfilled": won, "turn": game.turn}


def set_ambition(game, house_name: str, family: str,
                 target: Optional[str] = None):
    """Convenience: set the stake on a bare Game (used by UI verbs and
    tests that have not wired the facade)."""
    from gilded.chassis import Game
    if not isinstance(game, Game):
        raise TypeError("set_ambition needs a Game")
    return game.ambitions.set_ambition(house_name, family, target)


__all__ = [
    "AmbitionsFacade", "set_ambition",
    "AMBITION_REWARD", "STANCE_BACKS_AT", "STANCE_OPPOSES_AT",
    "FAMILY_DISPOSITION", "TARGETED_FAMILIES", "WANT_TEXT",
]
