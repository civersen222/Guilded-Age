"""
CivKings - Military Management System
Handles units, combat, movement, and military organization
"""
import random
from typing import List, Dict, Optional, Tuple
from game_data import UNIT_TYPES, UnitType


class Unit:
    """Represents a military unit on the map"""
    
    def __init__(self, unit_type: str, owner: str, position: tuple, moves_left: int = 1):
        self.unit_type = unit_type
        self.name = unit_type
        self.owner = owner
        self.owner_id = owner
        self.position = position
        self.moves_left = moves_left
        self.max_moves = 1
        self.xp = 0
        self.promotions: List[str] = []
        self.promotion = self.promotions[0] if self.promotions else None
        self.is_fortified = False
        self.hp = 100
        self.max_hp = 100
        self.is_alive = True
        stats = self.get_stats()
        self.attack = stats["attack"]
        self.defense = stats["defense"]
    
    def to_dict(self) -> dict:
        return {
            "unit_type": self.unit_type,
            "owner": self.owner,
            "position": self.position,
            "moves_left": self.moves_left,
            "xp": self.xp,
            "promotions": self.promotions,
            "hp": self.hp,
            "is_alive": self.is_alive
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get unit combat stats"""
        if self.unit_type in UNIT_TYPES:
            unit_data = UNIT_TYPES[self.unit_type]
            return {
                "attack": unit_data.attack,
                "defense": unit_data.defense,
                "movement": unit_data.movement,
                "cost": unit_data.production_cost
            }
        return {"attack": 10, "defense": 10, "movement": 1, "cost": 50}


class MilitaryManager:
    """Manages all military units and combat"""
    
    def __init__(self, units):
        if isinstance(units, dict):
            self.units = list(units.values())
        else:
            self.units = units
    
    def get_units_by_owner(self, owner: str) -> List[Unit]:
        """Get all units owned by a civilization"""
        return [unit for unit in self.units if unit.owner == owner and unit.is_alive]
    
    def move_unit(self, unit: Unit, new_position: tuple) -> bool:
        """Move a unit to a new position"""
        if unit.moves_left <= 0:
            return False
        
        # Check if position is valid (simplified)
        dx = abs(new_position[0] - unit.position[0])
        dy = abs(new_position[1] - unit.position[1])
        distance = max(dx, dy)  # Hex distance approximation
        
        if distance <= unit.moves_left:
            unit.position = new_position
            unit.moves_left -= distance
            
            # Check for landmark discovery
            if hasattr(self, 'map') and new_position in self.map.tiles:
                tile = self.map.tiles[new_position]
                if tile.landmark and not tile.landmark_discovered:
                    tile.landmark_discovered = True
                    landmark = LANDMARKS[tile.landmark]
                    # Apply landmark bonuses to the owner's resources
                    if hasattr(self, 'owner') and self.owner:
                        # Return discovery message
                        return f"Discovered {landmark.name}! +{landmark.gold_bonus} gold, +{landmark.food_bonus} food"
            
            return True
        return False
    
    def combat(self, attacker: Unit, defender: Unit) -> str:
        """Execute combat between two units"""
        if not attacker.is_alive or not defender.is_alive:
            return "One or both units are dead"
        
        # Get combat stats
        atk_stats = attacker.get_stats()
        def_stats = defender.get_stats()
        
        # Calculate combat power
        atk_power = atk_stats["attack"] + random.randint(-3, 3)
        def_power = def_stats["defense"] + random.randint(-3, 3)
        
        # Apply terrain bonuses (simplified)
        if defender.is_fortified:
            def_power += 5
        
        # Apply XP bonuses
        atk_power += attacker.xp // 10
        def_power += defender.xp // 10
        
        # Determine winner
        if atk_power > def_power:
            damage = max(10, atk_power - def_power)
            defender.hp -= damage
            attacker.xp += 5
            
            if defender.hp <= 0:
                defender.is_alive = False
                defender.hp = 0
                result = f"Attacker wins! {defender.unit_type} destroyed."
                attacker.promotions.append("veteran")
            else:
                result = f"Attacker wins! Dealt {damage} damage."
        else:
            damage = max(5, def_power - atk_power)
            attacker.hp -= damage
            defender.xp += 3
            
            if attacker.hp <= 0:
                attacker.is_alive = False
                attacker.hp = 0
                result = f"Defender wins! {attacker.unit_type} destroyed."
            else:
                result = f"Defender wins! Dealt {damage} damage."
        
        return result
    
    def process_turn(self):
        """Process end of turn for all units"""
        for unit in self.units:
            if unit.is_alive:
                unit.moves_left = unit.max_moves
                unit.is_fortified = False
    
    def add_unit(self, unit: Unit):
        """Add a unit to the manager"""
        self.units.append(unit)
    
    def remove_unit(self, unit: Unit):
        """Remove a unit from the manager"""
        if unit in self.units:
            self.units.remove(unit)
    
    def get_army_strength(self, owner: str) -> Dict[str, int]:
        """Get total army strength for a civilization"""
        units = self.get_units_by_owner(owner)
        total = {
            "attack": 0,
            "defense": 0,
            "count": len(units)
        }
        
        for unit in units:
            stats = unit.get_stats()
            total["attack"] += stats["attack"]
            total["defense"] += stats["defense"]
        
        return total
