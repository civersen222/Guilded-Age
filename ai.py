"""AI opponent logic: expansion, research, military strategy."""

from typing import Dict, List, Optional, Tuple
import random
from game_data import TECHNOLOGIES, TechBranch, Era, CIVILIZATIONS, UnitCategory


class AIPlayer:
    """Simulates an opponent civilization's decisions."""

    def __init__(self, civ_name: str, difficulty: str = "medium"):
        self.civ = CIVILIZATIONS.get(civ_name, CIVILIZATIONS["Rome"])
        self.difficulty = difficulty
        self.aggression: float = self._set_aggression()
        self.priorities: Dict[str, float] = {
            "military": 0.0,
            "science": 0.0,
            "economy": 0.0,
            "expansion": 0.0,
        }
        self._set_priorities()
        self.target_research: Optional[str] = None
        self.last_action: str = "idle"

    def _set_aggression(self) -> float:
        levels = {"easy": 0.2, "medium": 0.5, "hard": 0.8}
        return levels.get(self.difficulty, 0.5)

    def _set_priorities(self):
        if self.difficulty == "easy":
            self.priorities = {"military": 0.2, "science": 0.3, "economy": 0.3, "expansion": 0.2}
        elif self.difficulty == "medium":
            self.priorities = {"military": 0.4, "science": 0.3, "economy": 0.2, "expansion": 0.1}
        else:
            self.priorities = {"military": 0.6, "science": 0.2, "economy": 0.1, "expansion": 0.1}

    def decide_next_action(self, current_tech: List[str], cities_count: int,
                           military_strength: int, available_gold: float) -> Dict[str, any]:
        """AI decides what to do this turn. Returns action dict."""
        action = {
            "type": "research",
            "target": None,
            "build": None,
            "expand": False,
            "attack": False,
            "diplo_action": None,
        }

        # Decide research priority
        action["type"] = self._choose_research_priority(current_tech)

        # Decide production
        if self.priorities["military"] > 0.4 and military_strength < 50:
            action["build"] = self._choose_military_unit()
        elif self.priorities["economy"] > 0.3:
            action["build"] = "Worker"
        elif self.priorities["expansion"] > 0.3 and cities_count < 5:
            action["expand"] = True
            action["build"] = "Settler"

        # Decide military action
        if random.random() < self.aggression and military_strength > 30:
            action["attack"] = True

        # Decide diplomacy
        if self.aggression < 0.3:
            action["diplo_action"] = random.choice(["form_alliance", "trade"])
        elif self.aggression > 0.7:
            action["diplo_action"] = random.choice(["declare_war", "demand_tribute"])

        self.last_action = action["type"]
        return action

    def _choose_research_priority(self, current_tech: List[str]) -> str:
        if random.random() < self.priorities["science"]:
            return "science"
        elif random.random() < self.priorities["military"]:
            return "military"
        else:
            return "economy"

    def _choose_military_unit(self) -> str:
        units = ["Swordsman", "Archer", "Knight", "Siege Tower"]
        return random.choice(units)

    def get_opinion_on_player(self) -> float:
        """Simulate AI's opinion of the player. -100 to 100."""
        base = 50
        if self.aggression > 0.6:
            base -= 20
        elif self.aggression < 0.3:
            base += 10
        return base + random.randint(-10, 10)

    def get_ai_summary(self) -> str:
        lines = [
            f"\n=== AI ({self.civ.name}) Status ===",
            f"Difficulty: {self.difficulty}",
            f"Aggression: {self.aggression:.1f}",
            f"Last Action: {self.last_action}",
            "Priorities:",
        ]
        for p, v in self.priorities.items():
            lines.append(f"  {p}: {v:.1f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "civ_name": self.civ.name,
            "difficulty": self.difficulty,
            "aggression": self.aggression,
            "priorities": self.priorities,
            "last_action": self.last_action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AIPlayer':
        ai = cls(data["civ_name"], data["difficulty"])
        ai.aggression = data["aggression"]
        ai.priorities = data["priorities"]
        ai.last_action = data["last_action"]
        return ai
