"""Court positions: Marshal, Spymaster, Chancellor, Steward, Chaplain."""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional

from simulation import Character


class CourtPosition(Enum):
    MARSHAL = "Marshal"
    SPYMASTER = "Spymaster"
    CHANCELLOR = "Chancellor"
    STEWARD = "Steward"
    CHAPLAIN = "Chaplain"


class Court:
    """Manages the ruler's court positions and their bonuses."""

    POSITION_STATS: Dict[CourtPosition, str] = {
        CourtPosition.MARSHAL: "martial",
        CourtPosition.SPYMASTER: "intrigue",
        CourtPosition.CHANCELLOR: "diplomacy",
        CourtPosition.STEWARD: "stewardship",
        CourtPosition.CHAPLAIN: "diplomacy",
    }

    def __init__(self, ruler: Character):
        self.ruler = ruler
        self.positions: Dict[CourtPosition, Optional[Character]] = {p: None for p in CourtPosition}
        self.appointment_turns: Dict[CourtPosition, int] = {}

    def appoint(self, position: CourtPosition, character: Character, turn: int) -> bool:
        if character.id == self.ruler.id:
            return False
        # Check if character is already in another position
        for pos, char in self.positions.items():
            if char and char.id == character.id:
                return False
        old = self.positions[position]
        if old and hasattr(old, "set_court_position"):
            old.set_court_position("")
        self.positions[position] = character
        self.appointment_turns[position] = turn
        if hasattr(character, "set_court_position"):
            character.set_court_position(position.value)
        return True

    def dismiss(self, position: CourtPosition) -> Optional[Character]:
        char = self.positions[position]
        if char is None:
            return None
        if hasattr(char, "set_court_position"):
            char.set_court_position("")
        self.positions[position] = None
        return char

    def get_bonus(self, position: CourtPosition) -> int:
        char = self.positions[position]
        if char is None or not char.is_alive:
            return 0
        stat = self.POSITION_STATS.get(position)
        return char.get_effective_stat(stat) if stat else 0

    def get_bonus_for_stat(self, stat: str) -> int:
        total = 0
        for pos, stat_name in self.POSITION_STATS.items():
            if stat_name == stat:
                total += self.get_bonus(pos)
        return total

    @property
    def filled_count(self) -> int:
        return sum(1 for v in self.positions.values() if v is not None)

    def get_best_candidate(self, candidates: List[Character], position: CourtPosition) -> Optional[Character]:
        stat = self.POSITION_STATS.get(position)
        if not stat or not candidates:
            return None
        return max(candidates, key=lambda c: c.get_effective_stat(stat))

    def status_report(self) -> str:
        lines = [f"=== Court of {self.ruler.name} ({self.filled_count}/5 filled) ==="]
        for pos in CourtPosition:
            char = self.positions[pos]
            if char and char.is_alive:
                bonus = self.get_bonus(pos)
                lines.append(f"  {pos.value:12s} <- {char.name:20s} (bonus: +{bonus})")
            else:
                lines.append(f"  {pos.value:12s} <- VACANT")
        return "\n".join(lines)
