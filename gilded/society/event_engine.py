"""Situation renderer (spec Wave EV, M41).

A Situation is a fact that ALREADY happened - the caller applies the
state-delta first, then hands the engine the actors and the kind. The
engine picks a template from the content pool for that kind, fills the
slots and returns prose. Same situation twice -> different text, same
state effect.
"""
import random
from typing import Dict, List

from gilded.society.event_content.core_pools import TEMPLATE_POOLS


class Situation:
    """One narratable fact: kind + actor slots + extra string slots."""

    def __init__(self, kind: str, actors: Dict[str, object] = None,
                 cause: str = "", data: Dict[str, object] = None):
        self.kind = kind              # "succession", "mental_break", ...
        self.actors = actors or {}    # slot name -> Character
        self.cause = cause
        self.data = data or {}        # extra slot values (strings/numbers)


def render(situation: Situation) -> str:
    """Turn a Situation into one line of prose via the template pools."""
    pool = TEMPLATE_POOLS.get(situation.kind)
    slots: Dict[str, object] = dict(situation.data)
    if situation.cause:
        slots.setdefault("cause", situation.cause)
    for slot, char in situation.actors.items():
        slots[slot] = getattr(char, "name", str(char))
    if not pool:
        return str(slots.get("cause") or situation.kind)
    return random.choice(pool).format(**slots)


def choices_for(situation: Situation) -> List[Dict]:
    """Choices for a player-facing situation, built from what the subject
    can actually do (attribute-gated); shaped for CKEvent choices."""
    subject = situation.actors.get("subject") or situation.actors.get("new")
    choices: List[Dict] = [{"name": "Accept it", "effects": {}}]
    if subject is None:
        return choices
    if subject.get_effective_stat("resolve") >= 8:
        choices.append({"name": "Master yourself (+1 resolve)",
                        "effects": {"resolve": 1}})
    if subject.get_effective_stat("statecraft") >= 8:
        choices.append({"name": "Spin the story at court (+5 morale)",
                        "effects": {"morale": 5}})
    if subject.get_effective_stat("intrigue") >= 8:
        choices.append({"name": "Bury the whispers (drifts toward Deceitful)",
                        "effects": {"drift": {"honest_deceitful": 5}}})
    return choices
