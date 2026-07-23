"""Standing directives: the ruler's five dials of state (spec section 6).

The player does not micromanage; they set stances (-100..+100) on five
domains and seated executors carry them out. An executor whose conviction
sits far from the stance accrues friction: stress every turn, and after
enough consecutive conflicted turns, a chance to resign the seat."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DIRECTIVE_KEYS = ("capital", "labor", "expansion", "diplomacy", "war")

# directive -> conviction spectrum consulted for friction
DIRECTIVE_CONVICTION = {
    "capital": "traditionalist_modernist",         # +100 = modernize/invest hard
    "labor": "labor_capital",                      # +100 = break them
    "expansion": "preservationist_extractionist",  # +100 = acquire/extract
    "diplomacy": "nationalist_cosmopolitan",       # +100 = confront
    "war": "militarist_pacifist",                  # +100 = escalate
}

FRICTION_THRESHOLD = 60.0     # |stance - conviction| beyond this generates friction
FRICTION_STRESS = 8           # stress per turn on a conflicted executor
RESIGN_FRICTION_TURNS = 4     # consecutive conflicted turns before resignation risk
RESIGN_CHANCE = 0.25


@dataclass
class Directives:
    stances: Dict[str, int] = field(
        default_factory=lambda: {k: 0 for k in DIRECTIVE_KEYS})
    friction_turns: Dict[str, int] = field(default_factory=dict)  # key -> consecutive turns
    _policy_targets: Optional[Dict[str, int]] = field(default=None, repr=False)

    def set_stance(self, key: str, value: int) -> None:
        """Clamp to -100..100; changing course resets the friction counter."""
        self.stances[key] = max(-100, min(100, int(value)))
        self.friction_turns[key] = 0


def friction(stance: int, conviction: float) -> float:
    """How hard the order grates: distance beyond the tolerance threshold.

    The caller looks up conviction as
    executor.dispositions[DIRECTIVE_CONVICTION[key]]."""
    return max(0.0, abs(stance - conviction) - FRICTION_THRESHOLD)


def tick_friction(directives: Directives, seats: Dict[str, object],
                  rng: random.Random) -> List[Tuple[str, str]]:
    """One turn of grinding between stances and the people executing them.

    seats maps directive key -> seated Character (or None). Conflicted
    executors take FRICTION_STRESS; after RESIGN_FRICTION_TURNS consecutive
    conflicted turns each further turn risks resignation (RESIGN_CHANCE).
    Returns [(key, "stress" | "resigned"), ...]; on "resigned" the caller
    vacates the seat."""
    events: List[Tuple[str, str]] = []
    for key in DIRECTIVE_KEYS:
        char = seats.get(key)
        if char is None or not getattr(char, "is_alive", False):
            continue
        conviction = char.dispositions.get(DIRECTIVE_CONVICTION[key], 0.0)
        if friction(directives.stances.get(key, 0), conviction) <= 0:
            directives.friction_turns[key] = 0
            continue
        directives.friction_turns[key] = directives.friction_turns.get(key, 0) + 1
        char.add_stress(FRICTION_STRESS)
        if (directives.friction_turns[key] >= RESIGN_FRICTION_TURNS
                and rng.random() < RESIGN_CHANCE):
            directives.friction_turns[key] = 0
            events.append((key, "resigned"))
        else:
            events.append((key, "stress"))
    return events
