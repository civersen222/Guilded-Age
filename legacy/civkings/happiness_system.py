"""
CivKings - Happiness System
Manages citizen happiness, luxury resources, entertainment buildings,
overextension penalties, and happiness-driven effects.
"""
from typing import Dict, List, Optional, Set


class HappinessSystem:
    """Manages happiness across the empire and its effects on gameplay."""

    # Luxury resources and their happiness bonuses
    LUXURY_RESOURCES: Dict[str, int] = {
        "Wine": 4, "Oil": 4, "Ivory": 5, "Spices": 5,
        "Fur": 3, "Pearls": 5, "Incense": 4, "Tapestries": 5,
        "Marble": 4, "Silk": 6, "Gold_Ornaments": 5, "Exotic_Animals": 6,
    }

    # Entertainment buildings and their happiness bonuses
    ENTERTAINMENT_BUILDINGS: Dict[str, int] = {
        "Theater": 3, "Colosseum": 5, "Gardens": 4,
        "Temple_of_Festivals": 6, "Public_Baths": 3, "Palace_Gardens": 5,
    }

    # Rebellion thresholds
    REBELLION_THRESHOLDS = {
        "critical": 20,   # < 20%: high rebellion risk
        "low": 40,        # < 40%: moderate rebellion risk
        "unhappy": 60,    # < 60%: growth penalty
    }

    def __init__(self):
        self.base_happiness: int = 100
        self._luxury_resources: Set[str] = set()
        self._entertainment_buildings: Set[str] = set()
        self._city_count: int = 1
        self._max_cities_before_penalty: int = 5
        self._war_active: bool = False
        self._conquest_count: int = 0
        self._stability_modifier: float = 1.0
        self._tax_penalty_value: float = 0.0

    @property
    def luxury_bonus(self) -> int:
        """Calculate total happiness from luxury resources."""
        total = 0
        for resource in self._luxury_resources:
            total += self.LUXURY_RESOURCES.get(resource, 1)
        return total

    @property
    def entertainment_bonus(self) -> int:
        """Calculate total happiness from entertainment buildings."""
        total = 0
        for building in self._entertainment_buildings:
            total += self.ENTERTAINMENT_BUILDINGS.get(building, 1)
        return total

    @property
    def overextension_penalty(self) -> int:
        """Calculate happiness penalty from overextension."""
        if self._city_count <= self._max_cities_before_penalty:
            return 0
        excess = self._city_count - self._max_cities_before_penalty
        penalty_per_city = 5
        return excess * penalty_per_city

    @property
    def war_penalty(self) -> int:
        """Calculate happiness penalty from active war."""
        if self._war_active:
            return 10
        return 0

    @property
    def conquest_penalty(self) -> int:
        """Calculate happiness penalty from recent conquests."""
        return self._conquest_count * 3

    @property
    def tax_penalty(self) -> float:
        """Calculate happiness penalty from taxation (0-100% returns 0-60 points)."""
        # This will be set externally via set_tax_rate()
        return self._tax_penalty_value

    @tax_penalty.setter
    def tax_penalty(self, value: float):
        """Set the tax-related happiness penalty."""
        self._tax_penalty_value = value

    @property
    def current_happiness(self) -> int:
        """Calculate current happiness level."""
        happiness = self.base_happiness
        happiness += self.luxury_bonus
        happiness += self.entertainment_bonus
        happiness -= self.overextension_penalty
        happiness -= self.war_penalty
        happiness -= self.conquest_penalty
        happiness -= int(self.tax_penalty)
        happiness = max(0, min(100, happiness))
        return happiness

    @property
    def is_happy(self) -> bool:
        return self.current_happiness >= 60

    @property
    def is_unhappy(self) -> bool:
        return self.current_happiness < 40

    @property
    def is_rebelling(self) -> bool:
        return self.current_happiness < 20

    def add_luxury_resource(self, resource_name: str):
        """Add a luxury resource to the empire."""
        self._luxury_resources.add(resource_name)

    def remove_luxury_resource(self, resource_name: str):
        """Remove a luxury resource from the empire."""
        self._luxury_resources.discard(resource_name)

    def add_entertainment_building(self, building_name: str):
        """Add an entertainment building."""
        self._entertainment_buildings.add(building_name)

    def remove_entertainment_building(self, building_name: str):
        """Remove an entertainment building."""
        self._entertainment_buildings.discard(building_name)

    def update_city_count(self, city_count: int):
        """Update the number of cities for overextension calculation."""
        self._city_count = city_count

    def set_war_status(self, at_war: bool):
        """Set whether the empire is at war."""
        self._war_active = at_war

    def record_conquest(self, count: int = 1):
        """Record new conquests."""
        self._conquest_count += count

    def update_stability(self, stability: float):
        """Update stability modifier (affects happiness retention)."""
        self._stability_modifier = stability

    def get_production_loss(self) -> float:
        """Get production loss multiplier due to unhappiness (0-1, where 1 = no loss)."""
        if self.current_happiness >= 60:
            return 1.0
        elif self.current_happiness >= 40:
            return 0.8  # 20% loss
        elif self.current_happiness >= 20:
            return 0.5  # 50% loss
        else:
            return 0.25  # 75% loss

    def get_growth_penalty(self) -> float:
        """Get growth penalty (0-1, where 1 = no penalty)."""
        if self.current_happiness >= 60:
            return 1.0
        elif self.current_happiness >= 40:
            return 0.7  # 30% penalty
        elif self.current_happiness >= 20:
            return 0.4  # 60% penalty
        else:
            return 0.1  # 90% penalty

    def get_rebellion_chance(self) -> float:
        """Get rebellion chance per turn (0-1)."""
        if self.current_happiness >= 60:
            return 0.0
        elif self.current_happiness >= 40:
            return 0.01  # 1% chance
        elif self.current_happiness >= 20:
            return 0.05  # 5% chance
        else:
            return 0.20  # 20% chance

    def get_tax_rate_for_happiness(self, target_happiness: int = 60) -> int:
        """Calculate the maximum tax rate to achieve target happiness."""
        # Reverse-engineer tax rate from desired happiness
        other_bonuses = self.luxury_bonus + self.entertainment_bonus
        other_penalties = self.overextension_penalty + self.war_penalty + self.conquest_penalty
        net_before_tax = self.base_happiness + other_bonuses - other_penalties
        max_tax = net_before_tax - target_happiness
        return max(0, min(100, 100 - (max_tax * 100 / 100)))  # Simplified

    def get_effects_summary(self) -> Dict[str, any]:
        """Get summary of happiness effects."""
        return {
            "base_happiness": self.base_happiness,
            "luxury_bonus": self.luxury_bonus,
            "entertainment_bonus": self.entertainment_bonus,
            "overextension_penalty": self.overextension_penalty,
            "war_penalty": self.war_penalty,
            "conquest_penalty": self.conquest_penalty,
            "tax_penalty": int(self.tax_penalty),
            "current_happiness": self.current_happiness,
            "production_loss": 1.0 - self.get_production_loss(),
            "growth_penalty": 1.0 - self.get_growth_penalty(),
            "rebellion_chance": self.get_rebellion_chance() * 100,
            "status": self._get_status_label(),
        }

    def _get_status_label(self) -> str:
        """Get human-readable happiness status."""
        if self.current_happiness >= 90:
            return "Euphoric"
        elif self.current_happiness >= 80:
            return "Delighted"
        elif self.current_happiness >= 70:
            return "Content"
        elif self.current_happiness >= 60:
            return "Satisfied"
        elif self.current_happiness >= 50:
            return "Neutral"
        elif self.current_happiness >= 40:
            return "Unhappy"
        elif self.current_happiness >= 30:
            return "Angry"
        elif self.current_happiness >= 20:
            return "Furious"
        else:
            return "Revolt Risk"

    def add_luxury_resource(self, resource_name: str):
        """Add a luxury resource to the empire."""
        self._luxury_resources.add(resource_name)

    def remove_luxury_resource(self, resource_name: str):
        """Remove a luxury resource from the empire."""
        self._luxury_resources.discard(resource_name)

    def add_entertainment_building(self, building_name: str):
        """Add an entertainment building."""
        self._entertainment_buildings.add(building_name)

    def remove_entertainment_building(self, building_name: str):
        """Remove an entertainment building."""
        self._entertainment_buildings.discard(building_name)
