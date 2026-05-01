"""
CivKings - Faction System
Manages political factions (Nobles, Religious, Popular) and their influence on the game.
"""
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Faction:
    """A political faction within a civilization."""
    name: str
    faction_type: str  # "nobles", "religious", "popular"
    influence: int = 0  # 0-100
    support: int = 0  # 0-100 (how much the ruler supports them)
    members: List[str] = field(default_factory=list)
    demands: List[str] = field(default_factory=list)
    stability_effect: float = 0.0

    @property
    def is_dominant(self) -> bool:
        return self.influence >= 70

    @property
    def is_marginalized(self) -> bool:
        return self.influence <= 20

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "faction_type": self.faction_type,
            "influence": self.influence,
            "support": self.support,
            "members": self.members,
            "demands": self.demands,
            "stability_effect": self.stability_effect
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Faction':
        return cls(**data)


class FactionManager:
    """Manages factions for a single civilization."""

    FACTION_TYPES = {
        "nobles": {
            "name": "Noble Court",
            "description": "The aristocratic landowners and nobility",
            "base_influence": 40,
            "demands": ["Land grants", "Tax exemptions", "Military command positions"],
            "bonuses": {"stability": 5, "military": 10},
            "penalties": {"happiness": -5, "gold": -10}
        },
        "religious": {
            "name": "Religious Order",
            "description": "The clergy and religious institutions",
            "base_influence": 30,
            "demands": ["Temple construction", "Religious festivals", "Inquisition powers"],
            "bonuses": {"culture": 10, "happiness": 5},
            "penalties": {"gold": -5, "science": -5}
        },
        "popular": {
            "name": "Popular Assembly",
            "description": "The commoners and merchant guilds",
            "base_influence": 30,
            "demands": ["Price controls", "Public works", "Tax reductions"],
            "bonuses": {"gold": 10, "happiness": 5},
            "penalties": {"stability": -5, "military": -5}
        }
    }

    def __init__(self, civilization_name: str):
        self.civilization_name = civilization_name
        self.factions: Dict[str, Faction] = {}
        self.dominant_faction: Optional[Faction] = None
        self.conflict_level: float = 0.0  # 0-100
        self.recent_events: List[str] = []

    def initialize_factions(self) -> None:
        """Create initial factions for this civilization."""
        for faction_type, data in self.FACTION_TYPES.items():
            faction = Faction(
                name=f"{data['name']} of {self.civilization_name}",
                faction_type=faction_type,
                influence=data['base_influence'],
                support=50,
                demands=data['demands'][:],
                stability_effect=0.0
            )
            # Add random members
            member_count = random.randint(3, 8)
            for i in range(member_count):
                faction.members.append(f"{faction_type.capitalize()} Member {i+1}")
            self.factions[faction_type] = faction
        self._update_dominant_faction()

    def _update_dominant_faction(self) -> None:
        """Update which faction is currently dominant."""
        if not self.factions:
            self.dominant_faction = None
            return
        self.dominant_faction = max(self.factions.values(), key=lambda f: f.influence)

    def get_faction_effects(self) -> Dict[str, float]:
        """Calculate combined effects of all factions."""
        effects = {
            "stability": 0.0,
            "happiness": 0.0,
            "gold": 0.0,
            "culture": 0.0,
            "science": 0.0,
            "military": 0.0
        }

        for faction in self.factions.values():
            if faction.is_dominant:
                # Dominant faction provides bonuses
                for stat, bonus in self.FACTION_TYPES[faction.faction_type]['bonuses'].items():
                    effects[stat] += bonus * 0.1
            elif faction.is_marginalized:
                # Marginalized faction causes penalties
                for stat, penalty in self.FACTION_TYPES[faction.faction_type]['penalties'].items():
                    effects[stat] += penalty * 0.05

        # Conflict penalty
        if self.conflict_level > 50:
            effects['stability'] -= (self.conflict_level - 50) * 0.1

        return effects

    def adjust_influence(self, faction_type: str, amount: float) -> bool:
        """Adjust faction influence by a given amount."""
        if faction_type not in self.factions:
            return False

        faction = self.factions[faction_type]
        old_influence = faction.influence
        faction.influence = max(0, min(100, faction.influence + amount))

        # Check for significant changes
        if abs(faction.influence - old_influence) > 10:
            event = f"{faction.name} influence {'increased' if amount > 0 else 'decreased'} by {abs(amount):.0f}"
            self.recent_events.append(event)
            self._check_faction_events(faction)

        self._update_dominant_faction()
        self._update_conflict_level()
        return True

    def _check_faction_events(self, faction: Faction) -> None:
        """Check for special faction events."""
        if faction.influence >= 90 and not faction.is_dominant:
            event = f"⚠️ {faction.name} is about to seize power!"
            self.recent_events.append(event)
        elif faction.influence <= 5:
            event = f"💤 {faction.name} has been marginalized"
            self.recent_events.append(event)

    def _update_conflict_level(self) -> None:
        """Calculate conflict level between factions."""
        if len(self.factions) < 2:
            self.conflict_level = 0
            return

        influences = [f.influence for f in self.factions.values()]
        max_influence = max(influences)
        min_influence = min(influences)
        self.conflict_level = (max_influence - min_influence) / 2.0

    def satisfy_demand(self, faction_type: str, demand_index: int = 0) -> bool:
        """Satisfy a faction's demand, increasing their influence."""
        if faction_type not in self.factions:
            return False

        faction = self.factions[faction_type]
        if demand_index < len(faction.demands):
            demand = faction.demands.pop(demand_index)
            self.adjust_influence(faction_type, 15)
            event = f"✅ Satisfied {faction.name}'s demand: '{demand}'"
            self.recent_events.append(event)
            return True
        return False

    def suppress_faction(self, faction_type: str) -> bool:
        """Suppress a faction, decreasing their influence but reducing stability."""
        if faction_type not in self.factions:
            return False

        faction = self.factions[faction_type]
        self.adjust_influence(faction_type, -30)
        event = f"🔒 Suppressed {faction.name}"
        self.recent_events.append(event)
        return True

    def get_status(self) -> Dict:
        """Get current faction status."""
        return {
            "dominant_faction": self.dominant_faction.name if self.dominant_faction else None,
            "conflict_level": self.conflict_level,
            "factions": {ft: f.to_dict() for ft, f in self.factions.items()},
            "recent_events": self.recent_events[-5:]
        }

    def add_event(self, event: str) -> None:
        """Add a faction-related event."""
        self.recent_events.append(event)
        if len(self.recent_events) > 20:
            self.recent_events = self.recent_events[-20:]


class FactionEventGenerator:
    """Generates faction-related events."""

    @staticmethod
    def generate_faction_event(faction_manager: FactionManager) -> Optional[str]:
        """Generate a random faction event."""
        if not faction_manager.factions:
            return None

        event_type = random.choice([
            "demand", "conflict", "alliance", "scandal", "success"
        ])

        faction_type = random.choice(list(faction_manager.factions.keys()))
        faction = faction_manager.factions[faction_type]

        if event_type == "demand":
            if faction.demands:
                demand = faction.demands[0]
                return f"📜 The {faction.name} demands: '{demand}'"
        elif event_type == "conflict":
            if faction_manager.conflict_level > 30:
                return f"⚔️ Growing tensions between factions over '{random.choice(['power', 'resources', 'ideology'])}'"
        elif event_type == "alliance":
            faction_types = list(faction_manager.factions.keys())
            if len(faction_types) >= 2:
                other_type = random.choice([ft for ft in faction_types if ft != faction_type])
                return f"🤝 The {faction_manager.factions[faction_type].name} has allied with the {faction_manager.factions[other_type].name}"
        elif event_type == "scandal":
            return f"🕵️ Scandal rocks the {faction.name} - influence reduced"
        elif event_type == "success":
            faction_manager.adjust_influence(faction_type, 10)
            return f"🎉 The {faction.name} achieves a political victory!"

        return None
