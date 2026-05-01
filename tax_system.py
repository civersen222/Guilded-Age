"""
CivKings - Tax System
Handles tax rates, tax income, and effects on happiness/growth.
"""
from typing import Dict, List, Optional


class TaxSystem:
    """Manages tax policy and its effects on the economy."""

    TAX_RATES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    
    # Gold multiplier at each tax tier (0-100)
    # Low taxes encourage commerce; high taxes extract more but with diminishing returns
    GOLD_MULTIPLIER = {
        0: 0.0, 5: 0.35, 10: 0.7, 15: 1.05, 20: 1.4, 25: 1.75,
        30: 2.1, 35: 2.45, 40: 2.8, 45: 3.15, 50: 3.5, 55: 3.8,
        60: 4.0, 65: 4.15, 70: 4.25, 75: 4.3, 80: 4.3, 85: 4.25,
        90: 4.15, 95: 4.0, 100: 3.75  # Peak at ~75-80%, then diminishing due to corruption/avoidance
    }
    
    # Happiness penalty per percentage point above 50%
    HAPPINESS_PENALTY_RATE = 0.06  # per 1% above 50
    
    # Growth penalty per percentage point above 50%
    GROWTH_PENALTY_RATE = 0.02  # per 1% above 50

    def __init__(self, base_tax_rate: int = 30):
        self.tax_rate = max(0, min(100, base_tax_rate))
        self._previous_gold_income = 0
        self._previous_happiness = 0

    @property
    def gold_multiplier(self) -> float:
        """Get the gold multiplier for the current tax rate."""
        # Interpolate between defined tiers
        rate = self.tax_rate
        lower = max(0, (rate // 5) * 5)
        upper = min(100, lower + 5)
        if lower == upper:
            return self.GOLD_MULTIPLIER.get(rate, 0)
        frac = (rate - lower) / 5.0
        return self.GOLD_MULTIPLIER[lower] + (self.GOLD_MULTIPLIER[upper] - self.GOLD_MULTIPLIER[lower]) * frac

    @property
    def happiness_penalty(self) -> float:
        """Get happiness penalty from current tax rate."""
        if self.tax_rate <= 50:
            return 0.0
        excess = self.tax_rate - 50
        return excess * self.HAPPINESS_PENALTY_RATE

    @property
    def growth_penalty(self) -> float:
        """Get growth penalty from current tax rate."""
        if self.tax_rate <= 50:
            return 0.0
        excess = self.tax_rate - 50
        return excess * self.GROWTH_PENALTY_RATE

    def calculate_tax_income(self, city_gold_income: int) -> int:
        """Calculate gold income from tax rate applied to city gold yields."""
        base = int(city_gold_income * self.gold_multiplier)
        return base

    def calculate_total_tax_income(self, cities_gold: Dict[str, int]) -> int:
        """Calculate total tax income from all cities."""
        total = 0
        for gold in cities_gold.values():
            total += self.calculate_tax_income(gold)
        return total

    def set_tax_rate(self, rate: int) -> None:
        """Set the tax rate (0-100)."""
        self.tax_rate = max(0, min(100, rate))

    def get_tax_trend(self) -> str:
        """Get trend arrow for tax rate."""
        if self.tax_rate > 50:
            return "↑"  # high taxes
        elif self.tax_rate < 30:
            return "↓"  # low taxes
        return "→"  # moderate

    def get_tax_description(self) -> str:
        """Get human-readable description of current tax policy."""
        if self.tax_rate == 0:
            return "No Taxes - Citizens happy but treasury empty"
        elif self.tax_rate <= 10:
            return "Peasant Levies - Minimal taxation"
        elif self.tax_rate <= 20:
            return "Light Taxation - Balanced approach"
        elif self.tax_rate <= 30:
            return "Standard Levy - Fair and steady"
        elif self.tax_rate <= 40:
            return "Heavy Taxation - Straining the populace"
        elif self.tax_rate <= 50:
            return "Exorbitant Tolls - Citizens growing restless"
        elif self.tax_rate <= 60:
            return "Extortion - Open resentment brewing"
        elif self.tax_rate <= 70:
            return "Predatory - Rebellion whispers"
        elif self.tax_rate <= 80:
            return "Tyranny - The people suffer"
        elif self.tax_rate <= 90:
            return "Despotism - On the brink of revolt"
        else:
            return "Blood Tax - The empire bleeds"

    def get_effects_summary(self) -> Dict[str, float]:
        """Get summary of tax effects."""
        return {
            "gold_multiplier": self.gold_multiplier,
            "happiness_penalty": self.happiness_penalty,
            "growth_penalty": self.growth_penalty,
            "net_happiness": max(0, 100 - self.happiness_penalty),
        }

    def process_tax_income(self, cities: Dict) -> int:
        """Calculate and return tax income from all cities."""
        total_income = 0
        for city in cities.values():
            base_income = city.population * 2  # 2 gold per citizen
            total_income += int(base_income * self.gold_multiplier)
        return total_income
