"""
CivKings - Tech Policy & Era System
Handles tech policies, era bonuses, and research speed modifiers
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from game_data import TECHNOLOGIES, Technology, Era, TechBranch


class PolicyType(Enum):
    """Types of government policies that affect tech research."""
    ACADEMY = "Academy"           # +10% science per district
    THEOCRATIC = "Theocratic"     # Science from faith conversion
    MILITARIST = "Militarist"     # Science from conquest
    COMMERCIAL = "Commercial"     # Science from trade routes
    PHILOSOPHICAL = "Philosophical"  # Science from culture
    INDUSTRIAL = "Industrial"     # Production → Science conversion


class PolicyCommitment(Enum):
    """Level of policy commitment."""
    LOOSE = "Loose"        # No penalties for switching
    MODERATE = "Moderate"  # 10 turn cooldown
    STRICT = "Strict"      # 20 turn cooldown, gold cost to switch


@dataclass
class TechPolicy:
    """A tech policy that modifies research."""
    policy_type: PolicyType
    commitment: PolicyCommitment
    active: bool = True
    
    def get_science_modifier(self, tech: Technology, manager: 'TechManager') -> float:
        """Calculate the science modifier from this policy."""
        if not self.active:
            return 0.0
        
        modifier = 0.0
        
        if self.policy_type == PolicyType.ACADEMY:
            # +10% science per campus district
            modifier += 0.10 * manager._get_district_count('campus')
        
        elif self.policy_type == PolicyType.THEOCRATIC:
            # +5% science per temple
            modifier += 0.05 * manager._get_district_count('temple')
        
        elif self.policy_type == PolicyType.MILITARIST:
            # +1% science per city in war
            modifier += 0.01 * manager._get_war_count()
        
        elif self.policy_type == PolicyType.COMMERCIAL:
            # +2% science per trade route
            modifier += 0.02 * manager._get_trade_route_count()
        
        elif self.policy_type == PolicyType.PHILOSOPHICAL:
            # +0.5% science per culture point
            modifier += 0.005 * manager._get_total_culture()
        
        elif self.policy_type == PolicyType.INDUSTRIAL:
            # Convert 10% production to science
            modifier += 0.10 * manager._get_production_to_science_ratio()
        
        # Apply commitment multiplier
        commitment_mult = {
            PolicyCommitment.LOOSE: 1.0,
            PolicyCommitment.MODERATE: 1.2,
            PolicyCommitment.STRICT: 1.5,
        }
        modifier *= commitment_mult.get(self.commitment, 1.0)
        
        return modifier


class EraBonus:
    """Bonuses granted by being in a specific era."""
    
    BONUS_TABLE = {
        Era.ANCIENT: {
            'bonus_type': 'starting_bonus',
            'description': '+1 settler, +25% barbarian combat strength',
            'effects': {'starting_settlers': 1, 'barbarian_resistance': 0.25},
        },
        Era.CLASSICAL: {
            'bonus_type': 'military',
            'description': '+10% melee combat strength, melee units cost -1 production',
            'effects': {'melee_strength_bonus': 0.10, 'melee_production_discount': 1},
        },
        Era.MEDIEVAL: {
            'bonus_type': 'defense',
            'description': '+15% city defense, walls grant +10% happiness',
            'effects': {'defense_bonus': 0.15, 'wall_happiness': 0.10},
        },
        Era.RENAISSANCE: {
            'bonus_type': 'diplomacy',
            'description': '+20% diplomacy weight, embassies grant +5% science',
            'effects': {'diplomacy_weight': 0.20, 'embassy_science': 0.05},
        },
        Era.INDUSTRIAL: {
            'bonus_type': 'industry',
            'description': '+15% rail movement, railways grant +5 gold per turn',
            'effects': {'rail_speed': 0.15, 'railway_gold': 5, 'production_bonus': 0.10},
        },
        Era.MODERN: {
            'bonus_type': 'technology',
            'description': '+20% research speed, +25% ranged combat strength',
            'effects': {'research_speed': 0.20, 'ranged_strength': 0.25, 'science_bonus': 0.30},
        },
    }
    
    @classmethod
    def get_era_bonus(cls, era: Era) -> Dict:
        """Get the bonus for being in a specific era."""
        return cls.BONUS_TABLE.get(era, {})
    
    @classmethod
    def get_all_effects(cls, era: Era, tech_manager: 'TechManager') -> Dict:
        """Get all active effects for an era."""
        bonus = cls.get_era_bonus(era)
        if not bonus:
            return {}
        
        effects = bonus.get('effects', {}).copy()
        
        # Apply cumulative bonuses from previous eras
        for prev_era in Era:
            if prev_era.value < era.value:
                prev_bonus = cls.get_era_bonus(prev_era)
                if prev_bonus:
                    prev_effects = prev_bonus.get('effects', {})
                    for key, value in prev_effects.items():
                        if key in effects:
                            if isinstance(effects[key], (int, float)):
                                effects[key] += value
                            else:
                                effects[key] = value
                        else:
                            effects[key] = value
        
        return effects


class ResearchSpeedModifier:
    """Calculates overall research speed modifiers."""
    
    def __init__(self, tech_manager: 'TechManager'):
        self.tech_manager = tech_manager
        self._active_modifiers: List[Tuple[str, float]] = []
    
    def add_modifier(self, source: str, amount: float):
        """Add a research speed modifier.
        
        Args:
            source: What's providing the modifier (e.g., "Policy", "Tech", "Wonder")
            amount: Percentage modifier (e.g., 0.25 for +25%)
        """
        # Remove existing modifier from same source
        self._active_modifiers = [
            (s, a) for s, a in self._active_modifiers if s != source
        ]
        self._active_modifiers.append((source, amount))
    
    def remove_modifier(self, source: str):
        """Remove a modifier by source."""
        self._active_modifiers = [
            (s, a) for s, a in self._active_modifiers if s != source
        ]
    
    def get_total_modifier(self) -> float:
        """Get the total research speed multiplier."""
        total = 1.0
        for _, amount in self._active_modifiers:
            total += amount
        return total
    
    def get_breakdown(self) -> List[Tuple[str, float]]:
        """Get a breakdown of all active modifiers."""
        return self._active_modifiers.copy()
    
    def calculate_effective_cost(self, tech: Technology) -> int:
        """Calculate the effective research cost of a tech with all modifiers."""
        base_cost = tech.cost
        
        # Apply policy modifiers
        policy_mod = 0.0
        for policy in self.tech_manager._policies:
            policy_mod += policy.get_science_modifier(tech, self.tech_manager)
        
        # Apply era bonuses
        current_era = self.tech_manager.get_current_era()
        era_bonus = EraBonus.get_era_bonus(current_era)
        if era_bonus:
            era_mod = era_bonus.get('effects', {}).get('research_speed', 0)
            policy_mod += era_mod
        
        # Apply total modifier
        effective_cost = base_cost / (1.0 + policy_mod) * self.get_total_modifier()
        
        return int(effective_cost)


class TechPolicyManager:
    """Manages tech policies and commitments."""
    
    def __init__(self, tech_manager: 'TechManager'):
        self.tech_manager = tech_manager
        self._policies: List[TechPolicy] = []
        self._active_policy: Optional[TechPolicy] = None
        self._last_switch_turn: int = 0
    
    def add_policy(self, policy_type: PolicyType, commitment: PolicyCommitment = PolicyCommitment.LOOSE) -> TechPolicy:
        """Add a new policy slot."""
        if len(self._policies) >= 4:  # Max 4 policy slots
            raise ValueError("Maximum policy slots reached (4)")
        
        policy = TechPolicy(policy_type=policy_type, commitment=commitment)
        self._policies.append(policy)
        return policy
    
    def activate_policy(self, policy: TechPolicy):
        """Activate a policy."""
        if policy not in self._policies:
            raise ValueError("Policy not found")
        
        # Check commitment cooldown
        if self._active_policy:
            turns_since_switch = self.tech_manager._current_turn - self._last_switch_turn
            
            if self._active_policy.commitment == PolicyCommitment.MODERATE and turns_since_switch < 10:
                raise ValueError("Policy on 10-turn cooldown")
            elif self._active_policy.commitment == PolicyCommitment.STRICT and turns_since_switch < 20:
                raise ValueError("Policy on 20-turn cooldown")
        
        # Deactivate previous
        if self._active_policy:
            self._active_policy.active = False
        
        policy.active = True
        self._active_policy = policy
        self._last_switch_turn = self.tech_manager._current_turn
    
    def deactivate_policy(self, policy: TechPolicy):
        """Deactivate a policy."""
        if policy == self._active_policy:
            self._active_policy = None
        policy.active = False
    
    def get_total_science_modifier(self, tech: Technology) -> float:
        """Get the total science modifier from all active policies."""
        total = 0.0
        for policy in self._policies:
            if policy.active:
                total += policy.get_science_modifier(tech, self.tech_manager)
        return total
    
    def can_switch_policy(self) -> bool:
        """Check if policy can be switched this turn."""
        if not self._active_policy:
            return True
        
        turns_since_switch = self.tech_manager._current_turn - self._last_switch_turn
        
        if self._active_policy.commitment == PolicyCommitment.MODERATE:
            return turns_since_switch >= 10
        elif self._active_policy.commitment == PolicyCommitment.STRICT:
            return turns_since_switch >= 20
        return True  # LOOSE
