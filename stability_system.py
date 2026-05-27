"""
CivKings - Stability System
Manages empire stability, unrest, and revolt risk.
Stability decreases with wars, succession, conquest, and overextension.
"""
from typing import Dict, List, Optional, Tuple


class StabilitySystem:
    """Manages political stability across the empire."""

    # Government type base stability
    GOVERNMENT_BASE = {
        "Monarchy": 80,
        "Oligarchy": 60,
        "Theocracy": 70,
        "Republic": 65,
        "Autocracy": 55,
        "Dynasty": 75,
    }

    # Events that affect stability
    EVENT_MODIFIERS = {
        "war_declared": -15,
        "war_won": 5,
        "war_lost": -20,
        "ruler_death": -10,
        "succession_crisis": -25,
        "conquest": -8,
        "rebellion_quelled": -12,
        "rebellion_succeeded": -30,
        "diplomatic_alliance": 5,
        "trade_deal": 3,
        "cultural_flourishing": 8,
        "golden_age": 15,
        "plague": -5,
        "natural_disaster": -10,
    }

    def __init__(self, government_type: str = "Monarchy"):
        self.government_type = government_type
        self.stability: float = self.GOVERNMENT_BASE.get(government_type, 50)
        self.unrest: float = 0.0
        self.revolt_risk: float = 0.0
        self._war_count: int = 0
        self._recent_conquests: int = 0
        self._rebellion_count: int = 0
        self._golden_age_active: bool = False
        self._golden_age_turns: int = 0
        self._previous_stability: float = self.stability

    @property
    def is_stable(self) -> bool:
        return self.stability >= 60

    @property
    def is_unstable(self) -> bool:
        return self.stability < 40

    @property
    def is_crisis(self) -> bool:
        return self.stability < 20

    @property
    def government_base(self) -> int:
        return self.GOVERNMENT_BASE.get(self.government_type, 50)

    def apply_change(self, amount: float) -> float:
        """Apply a raw stability change (no event type required)."""
        old_stability = self.stability
        self.stability = max(0, min(100, self.stability + amount))
        if amount < 0:
            self.unrest += abs(amount)
        return self.stability - old_stability

    def apply_event_modifier(self, event_type: str, amount: Optional[float] = None) -> float:
        """Apply stability modifier from an event."""
        if event_type not in self.EVENT_MODIFIERS:
            return 0.0
        
        modifier = amount if amount is not None else self.EVENT_MODIFIERS[event_type]
        old_stability = self.stability
        self.stability = max(0, min(100, self.stability + modifier))
        
        # Track unrest from negative modifiers
        if modifier < 0:
            self.unrest += abs(modifier)
        
        return self.stability - old_stability

    def update_war_status(self, at_war: bool, conquered_cities: int = 0):
        """Update stability based on war status and conquests."""
        if at_war:
            self._war_count += 1
        else:
            self._war_count = max(0, self._war_count - 1)
        
        if conquered_cities > 0:
            self._recent_conquests += conquered_cities

    def update_golden_age(self, active: bool, turns: int = 0):
        """Update golden age status."""
        self._golden_age_active = active
        self._golden_age_turns = turns

    def calculate_unrest(self) -> float:
        """Calculate current unrest level."""
        unrest = 0.0
        
        # War penalty
        if self._war_count > 0:
            unrest += self._war_count * 3
        
        # Conquest penalty
        unrest += self._recent_conquests * 2
        
        # Overextension (simplified)
        if self.stability < 50:
            unrest += 5
        
        # Golden age bonus
        if self._golden_age_active:
            unrest -= min(10, self._golden_age_turns * 0.5)
        
        return max(0, unrest)

    def calculate_revolt_risk(self) -> float:
        """Calculate probability of revolt (0-1)."""
        risk = 0.0
        
        if self.stability <= 20:
            risk = 0.5
        elif self.stability <= 40:
            risk = 0.2
        elif self.stability <= 60:
            risk = 0.05
        
        # Add unrest factor
        risk += self.unrest * 0.01
        
        # Cap at 1.0
        return min(1.0, risk)

    def check_revolt(self) -> bool:
        """Check if a revolt occurs this turn."""
        if self.calculate_revolt_risk() > 0:
            import random
            return random.random() < self.calculate_revolt_risk()
        return False

    def quench_revolt(self, success: bool = True) -> float:
        """Handle revolt outcome."""
        if success:
            self.stability = max(0, self.stability - 10)
            return -10
        else:
            self.stability = max(0, self.stability - 30)
            return -30

    def get_stability_trend(self) -> str:
        """Get trend arrow for stability."""
        delta = self.stability - self._previous_stability
        self._previous_stability = self.stability
        
        if delta > 5:
            return "UP"
        elif delta < -5:
            return "DOWN"
        return "SAME"

    def get_effects_summary(self) -> Dict[str, any]:
        """Get summary of stability effects."""
        return {
            "government_type": self.government_type,
            "base_stability": self.government_base,
            "current_stability": self.stability,
            "unrest": self.unrest,
            "revolt_risk": self.calculate_revolt_risk() * 100,
            "status": self._get_status_label(),
            "war_count": self._war_count,
            "conquest_count": self._recent_conquests,
        }

    def _get_status_label(self) -> str:
        """Get human-readable stability status."""
        if self.stability >= 90:
            return "Flourishing"
        elif self.stability >= 80:
            return "Strong"
        elif self.stability >= 70:
            return "Stable"
        elif self.stability >= 60:
            return "Firm"
        elif self.stability >= 50:
            return "Moderate"
        elif self.stability >= 40:
            return "Unstable"
        elif self.stability >= 30:
            return "Fragile"
        elif self.stability >= 20:
            return "Precarious"
        elif self.stability >= 10:
            return "Critical"
        else:
            return "On the Brink"
