"""
CivKings - Victory Condition Tracker
Handles victory conditions: Domination, Science, Culture, Diplomatic, Dynasty.
"""
from typing import Optional, Dict, List
from enum import Enum
from game_data import Era


class VictoryType(Enum):
    DOMINATION = "Domination Victory"
    SCIENCE = "Science Victory"
    CULTURE = "Culture Victory"
    DIPLOMACY = "Diplomatic Victory"
    DYNASTY = "Dynasty Victory"


class VictoryCondition:
    """A single victory condition with its threshold."""

    def __init__(
        self,
        victory_type: VictoryType,
        threshold: float,
        description: str = "",
    ):
        self.victory_type = victory_type
        self.threshold = threshold
        self.description = description or self._default_description()
        self.value: float = 0.0

    def _default_description(self) -> str:
        descriptions = {
            VictoryType.DOMINATION: "Control 50% of starting cities",
            VictoryType.SCIENCE: "Accumulate enough science to reach the next era",
            VictoryType.CULTURE: "Accumulate enough culture to influence the world",
            VictoryType.DIPLOMACY: "Have enough allied civilizations",
            VictoryType.DYNASTY: "Have your dynasty survive long enough",
        }
        return descriptions.get(self.victory_type, "Unknown victory condition")

    def add_progress(self, amount: float) -> None:
        """Add progress toward this victory condition."""
        self.value = min(self.value + amount, self.threshold * 10)  # Cap at 10x threshold

    def reset(self) -> None:
        """Reset progress."""
        self.value = 0.0


class VictoryConditionTracker:
    """Tracks all victory conditions and checks for victory."""

    def __init__(self):
        self.conditions: Dict[VictoryType, VictoryCondition] = {
            VictoryType.DOMINATION: VictoryCondition(VictoryType.DOMINATION, 10.0),
            VictoryType.SCIENCE: VictoryCondition(VictoryType.SCIENCE, 100.0),
            VictoryType.CULTURE: VictoryCondition(VictoryType.CULTURE, 1000.0),
            VictoryType.DIPLOMACY: VictoryCondition(VictoryType.DIPLOMACY, 5.0),
            VictoryType.DYNASTY: VictoryCondition(VictoryType.DYNASTY, 10.0),
        }
        self.victory_triggered: Optional[VictoryType] = None
        self.victory_turn: Optional[int] = None

    def check_victory(self) -> Optional[VictoryType]:
        """Check if any victory condition is met.

        Returns the first victory type that is met, or None.
        """
        if self.victory_triggered:
            return self.victory_triggered

        for vtype, condition in self.conditions.items():
            if condition.value >= condition.threshold:
                self.victory_triggered = vtype
                return vtype

        return None

    def add_progress(self, victory_type: VictoryType, amount: float) -> None:
        """Add progress to a specific victory condition."""
        if victory_type in self.conditions:
            self.conditions[victory_type].add_progress(amount)

    def set_progress(self, victory_type: VictoryType, value: float) -> None:
        """Set the progress of a specific victory condition."""
        if victory_type in self.conditions:
            self.conditions[victory_type].value = value

    def get_progress(self, victory_type: VictoryType) -> float:
        """Get the current progress of a victory condition."""
        if victory_type in self.conditions:
            return self.conditions[victory_type].value
        return 0.0

    def get_percentage(self, victory_type: VictoryType) -> float:
        """Get the percentage progress of a victory condition."""
        if victory_type in self.conditions:
            condition = self.conditions[victory_type]
            return (condition.value / condition.threshold) * 100 if condition.threshold > 0 else 0
        return 0.0

    def reset(self) -> None:
        """Reset all victory conditions."""
        for condition in self.conditions.values():
            condition.reset()
        self.victory_triggered = None
        self.victory_turn = None

    def get_active_victory_type(self) -> Optional[VictoryType]:
        """Get the type of victory that was triggered."""
        return self.victory_triggered

    def get_victory_description(self, victory_type: VictoryType) -> str:
        """Get the description of a victory condition."""
        if victory_type in self.conditions:
            return self.conditions[victory_type].description
        return "Unknown victory condition"

    def record_victory(self, player: str, victory_msg: str, turn: int) -> None:
        """Record a victory event."""
        self.victory_triggered = None
        for vtype in self.conditions:
            if vtype.value in victory_msg:
                self.victory_triggered = vtype
                break
        self.victory_turn = turn

    def get_victory_progress(self, player: str) -> str:
        """Get formatted victory progress for player."""
        lines = []
        for vtype in VictoryType:
            pct = self.get_percentage(vtype)
            lines.append(f"  {vtype.value}: {pct:.1f}%")
        return "\n".join(lines)
