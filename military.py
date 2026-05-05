"""
CivKings - Military Management System
Handles units, combat, movement, and military organization
"""
import random
from typing import List, Dict, Optional, Tuple
from game_data import UNIT_TYPES, UnitType, TERRAIN_DEFENSE_BONUS, TerrainType
from combat import CombatResult


class Unit:
    """Represents a military unit on the map"""
    
    # Promotion levels: (XP threshold, label, bonuses)
    PROMOTION_TIERS = [
        (50, "Novice", {"attack": 5}),
        (150, "Skilled", {"defense": 10}),
        (300, "Veteran", {"movement": 1}),
        (500, "Elite", {"attack": 15}),
        (750, "Champion", {"defense": 20}),
        (1000, "Grand Champion", {"attack": 10, "defense": 10}),
    ]
    
    def __init__(self, unit_type: str, owner: str, position: tuple, moves_left: Optional[int] = None):
        self.unit_type = unit_type
        self.name = unit_type
        self.owner = owner
        self.position = position
        self.xp = 0
        self.level = 1
        self.promotions: List[int] = []  # XP thresholds we've unlocked
        self.is_fortified = False
        self.hp = 100
        self.max_hp = 100
        self.is_alive = True
        self.last_combat_result = None
        self.kills = 0
        self.is_busy = False
        self.busy_type: str = ""
        self.busy_target: str = ""
        
        # Base stats from unit type
        base = self.get_base_stats()
        self.attack = base["attack"]
        self.defense = base["defense"]
        self.base_move = base["movement"]
        self.max_moves = self.base_move
        
        self.moves_left = moves_left if moves_left is not None else self.base_move
        
        # Check and apply promotions
        self.check_promotions()
        self._apply_promotion_bons()
    
    def _apply_promotion_bons(self) -> None:
        """Recalculate attack/defense/moves from base + active promotions."""
        base = self.get_base_stats()
        self.attack = base["attack"]
        self.defense = base["defense"]
        self.max_moves = self.base_move
        
        for xp_thresh, _, bonuses in self.PROMOTION_TIERS:
            if xp_thresh in self.promotions:
                for stat, val in bonuses.items():
                    if stat == "attack":
                        self.attack += val
                    elif stat == "defense":
                        self.defense += val
                    elif stat == "movement":
                        self.max_moves += val
    
    def check_promotions(self) -> List[str]:
        """Check if unit qualifies for new promotions based on accumulated XP.
        Returns list of new promotion labels unlocked this call."""
        new_labels = []
        for xp_thresh, label, _ in self.PROMOTION_TIERS:
            if xp_thresh <= self.xp and xp_thresh not in self.promotions:
                self.promotions.append(xp_thresh)
                new_labels.append(label)
        if new_labels:
            self._apply_promotion_bons()
            self.level = len(self.promotions) + 1
        return new_labels
    
    def get_base_stats(self) -> Dict[str, int]:
        """Get base unit stats without promotions."""
        if self.unit_type in UNIT_TYPES:
            u = UNIT_TYPES[self.unit_type]
            return {
                "attack": u.attack,
                "defense": u.defense,
                "movement": u.movement,
                "cost": u.production_cost,
            }
        return {"attack": 10, "defense": 10, "movement": 1, "cost": 50}
    
    def get_stats(self) -> Dict[str, int]:
        """Get current combat stats including promotions."""
        return {
            "attack": self.attack,
            "defense": self.defense,
            "movement": self.max_moves,
            "cost": self.get_base_stats()["cost"],
        }
    
    def to_dict(self) -> dict:
        return {
            "unit_type": self.unit_type,
            "owner": self.owner,
            "position": self.position,
            "xp": self.xp,
            "level": self.level,
            "promotions": self.promotions,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "is_alive": self.is_alive,
            "attack": self.attack,
            "defense": self.defense,
            "max_moves": self.max_moves,
        }
    
    def deal_damage(self, damage: int) -> bool:
        """Deal damage. Returns True if killed."""
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
            return True
        return False
    
    def heal(self, amount: int) -> None:
        """Heal unit, capped at max_hp."""
        self.hp = min(self.max_hp, self.hp + amount)


class MilitaryManager:
    """Manages all military units and combat."""
    
    def __init__(self, units: Optional[List[Unit]] = None):
        self.units: List[Unit] = units if units is not None else []
        self.map = None  # Optional reference to hex_map for terrain lookups
    
    def get_units_by_owner(self, owner: str) -> List[Unit]:
        """Get all living units owned by a civilization."""
        return [u for u in self.units if u.owner == owner and u.is_alive]
    
    def get_units_at_position(self, position: tuple) -> List[Unit]:
        """Get all living units at a position."""
        return [u for u in self.units if u.position == position and u.is_alive]
    
    def move_unit(self, unit: Unit, new_position: tuple) -> bool:
        """Move a unit. Returns True on success, False if can't move."""
        if unit.moves_left <= 0:
            return False
        
        dx = abs(new_position[0] - unit.position[0])
        dy = abs(new_position[1] - unit.position[1])
        distance = max(dx, dy)
        
        if distance > unit.moves_left:
            return False
        
        # Check for enemy unit at destination
        occupants = self.get_units_at_position(new_position)
        for occ in occupants:
            if occ.owner != unit.owner:
                # Combat triggered by moving into enemy tile
                result = self.combat(unit, occ)
                return result is not None
        
        unit.position = new_position
        unit.moves_left -= distance
        return True
    
    def combat(self, attacker: Unit, defender: Unit) -> Optional[CombatResult]:
        """Execute combat. Returns CombatResult or None if invalid."""
        if not attacker.is_alive or not defender.is_alive:
            return None
        
        # Base combat power
        atk_power = attacker.attack
        def_power = defender.defense
        
        # Randomness (±10)
        rng = random.randint(-10, 10)
        atk_power += rng
        def_power += rng
        
        # Terrain defense bonus for defender
        if self.map and hasattr(self.map, 'tiles'):
            tile = self.map.tiles.get(defender.position)
            if tile and hasattr(tile, 'terrain'):
                terrain_bonus = TERRAIN_DEFENSE_BONUS.get(tile.terrain, 0)
                def_power += terrain_bonus
        
        # Fortified bonus
        if defender.is_fortified:
            def_power += 10
        
        # XP bonus
        atk_power += attacker.xp // 50
        def_power += defender.xp // 50
        
        # Resolve combat using deal_damage for proper death handling
        result = CombatResult()
        att_was_alive = attacker.is_alive
        def_was_alive = defender.is_alive
        
        if atk_power > def_power:
            damage = max(10, atk_power - def_power)
            attacker.deal_damage(0)  # attacker takes no damage on win
            defender.deal_damage(damage)
            if def_was_alive and not defender.is_alive:
                attacker.kills += 1
            result.description = f"Attacker wins! {defender.unit_type} destroyed. (+{damage} dmg)"
        elif def_power > atk_power:
            damage = max(5, def_power - atk_power)
            attacker.deal_damage(damage)
            defender.deal_damage(0)  # defender takes no damage on win
            if att_was_alive and not attacker.is_alive:
                defender.kills += 1
            result.description = f"Defender wins! {attacker.unit_type} destroyed. (+{damage} dmg)"
        else:
            # Draw - both take small damage
            dmg = random.randint(5, 15)
            attacker.deal_damage(dmg)
            defender.deal_damage(dmg)
            result.description = f"Combat ended in a draw! Both took {dmg} damage."
        
        attacker.last_combat_result = result
        defender.last_combat_result = result
        return result
    
    def process_turn(self):
        """Reset moves and un-fortify all living units."""
        for unit in self.units:
            if unit.is_alive:
                unit.moves_left = unit.max_moves
                unit.is_fortified = False
    
    def add_unit(self, unit: Unit):
        self.units.append(unit)
    
    def remove_unit(self, unit: Unit):
        if unit in self.units:
            self.units.remove(unit)
    
    def get_army_strength(self, owner: str) -> Dict[str, int]:
        """Get total army strength for a civilization."""
        units = self.get_units_by_owner(owner)
        return {
            "attack": sum(u.attack for u in units),
            "defense": sum(u.defense for u in units),
            "count": len(units),
        }
