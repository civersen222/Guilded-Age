"""
CivKings - Military Management System
Handles units, combat, movement, and military organization
"""
import random
from typing import List, Dict, Optional, Tuple
from game_data import UNIT_TYPES, UnitType, TERRAIN_DEFENSE_BONUS, TerrainType, UnitCategory
from combat import CombatResult, resolve_combat


class Unit:
    """Represents a military unit on the map"""
    
    XP_PER_PROMOTION = 10  # XP needed for each promotion level
    
    def __init__(self, unit_type: str, owner: str, position: tuple, moves_left: Optional[int] = None):
        self.unit_type = unit_type
        self.name = unit_type
        self.owner = owner
        self.position = position
        self.xp = 0
        self.level = 1
        self.promotions: List[Dict[str, int]] = []  # e.g. [{"attack": 1}, {"defense": 1}]
        self.is_fortified = False
        self.hp = 100
        self.max_hp = 100
        self.is_alive = True
        self.last_combat_result = None
        self.kills = 0
        self.has_fought = False  # fought this turn; blocks healing (M30)
        self.is_busy = False
        self.busy_type: str = ""
        self.busy_target: str = ""
        self.pending_promotion: bool = False  # True when player must choose a promotion
        
        # Base stats from unit type
        base = self.get_base_stats()
        self.attack = base["attack"]
        self.defense = base["defense"]
        self.base_move = base["movement"]
        self.max_moves = self.base_move
        
        self.moves_left = moves_left if moves_left is not None else self.base_move
    
    def _apply_promotions(self) -> None:
        """Re-apply stat bonuses from all earned promotions."""
        base = self.get_base_stats()
        self.attack = base["attack"]
        self.defense = base["defense"]
        self.max_moves = self.base_move

        for bonus in self.promotions:
            for stat, val in bonus.items():
                if stat == "attack":
                    self.attack += val
                elif stat == "defense":
                    self.defense += val
                elif stat == "movement":
                    self.max_moves += val
    def gain_xp(self, amount: int) -> None:
        """Gain XP and check for promotion eligibility."""
        self.xp += amount
        if self.xp >= self.XP_PER_PROMOTION * self.level:
            self._offer_promotion()

    def _offer_promotion(self) -> None:
        """Mark unit as having a pending promotion for player to choose."""
        self.pending_promotion = True
        print(f"[PROMOTION] {self.name} ({self.owner}) has a pending promotion "
              f"(XP: {self.xp}, Level: {self.level})")

    def accept_promotion(self, choice: str) -> None:
        """Apply a player-chosen promotion. choice must be 'attack', 'defense', or 'movement'."""
        if not self.pending_promotion:
            return
        if choice not in ('attack', 'defense', 'movement'):
            return
        bonus = {choice: 1}
        self.promotions.append(bonus)
        self.level += 1
        self.pending_promotion = False
        self._apply_promotions()
        print(f"[PROMOTION] {self.name} ({self.owner}) promoted: +1 {choice} "
              f"(XP: {self.xp}, Level: {self.level})")
    def get_promotion_title(self) -> str:
        """Get current promotion title based on level."""
        titles = ["Conscript", "Trained", "Veteran", "Elite", "Champion", "Legendary"]
        idx = min(self.level - 1, len(titles) - 1)
        return titles[idx]

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
        self.game = None  # Optional reference to Game for ruler lookups (M29)
    
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
        """Execute combat through the tactical resolver (combat.py, M29)."""
        if not attacker.is_alive or not defender.is_alive:
            return None

        tile = None
        if self.map is not None and hasattr(self.map, 'tiles'):
            tile = self.map.tiles.get(defender.position)

        att_ruler = def_ruler = None
        if self.game is not None:
            att_ruler = self.game.rulers.get(attacker.owner)
            def_ruler = self.game.rulers.get(defender.owner)

        result = resolve_combat([attacker], [defender], tile, att_ruler, def_ruler)
        if self.game is not None:
            _t = getattr(self.game, "_telemetry", None)
            if _t is not None:
                _t["battles"] = _t.get("battles", 0) + 1

        attacker.has_fought = True
        defender.has_fought = True
        attacker.last_combat_result = result
        defender.last_combat_result = result
        return result
    
    def process_turn(self):
        """Per-turn upkeep (M30): reset moves, tick fortification, heal idle units."""
        for unit in self.units:
            if not unit.is_alive:
                continue
            unit.moves_left = unit.max_moves
            if unit.is_fortified:
                unit._fortify_turns = getattr(unit, "_fortify_turns", 0) + 1
            else:
                unit._fortify_turns = 0
            if getattr(unit, "has_fought", False):
                unit.has_fought = False
            elif unit.hp < unit.max_hp:
                unit.heal(10 if self._in_friendly_territory(unit) else 5)

    def _in_friendly_territory(self, unit) -> bool:
        """True when the unit stands on a tile owned by one of its own cities."""
        if self.game is None:
            return False
        for city in getattr(self.game, "cities", {}).values():
            if city.owner == unit.owner and unit.position in getattr(city, "owned_tiles", set()):
                return True
        return False

    def attack_city(self, unit, city) -> Optional[str]:
        """One unit assaults a city (M31). Returns a message, or None if invalid.

        Ranged/siege grind the city's HP and cannot capture; a melee or
        cavalry attack that drops the city to 0 HP captures it.
        """
        if not unit.is_alive or unit.moves_left <= 0 or city.owner == unit.owner:
            return None

        utype = UNIT_TYPES.get(unit.unit_type)
        category = utype.category if utype else UnitCategory.MELEE
        if category in (UnitCategory.SETTLER, UnitCategory.WORKER):
            return None

        strength = city.combat_strength()
        siege_mult = 2.0 if category == UnitCategory.SIEGE else 1.0
        dmg = max(1, int(unit.attack * siege_mult - strength * 0.5))
        city.hp -= dmg
        city.was_attacked = True
        unit.moves_left = 0
        unit.has_fought = True

        # The city strikes back at attackers storming the walls; ranged and
        # siege units batter from a distance and take nothing.
        if category in (UnitCategory.MELEE, UnitCategory.CAVALRY, UnitCategory.HELD):
            unit.deal_damage(int(strength * 0.5))

        if city.hp <= 0:
            if category in (UnitCategory.MELEE, UnitCategory.CAVALRY) and unit.is_alive:
                return self._capture_city(unit, city)
            city.hp = 1  # cannot capture; the city holds at the brink
            return f"{city.name} teeters at the brink of falling to {unit.owner}!"
        return (f"{unit.unit_type} of {unit.owner} assaults {city.name}: "
                f"-{dmg} (city HP {max(city.hp, 0)}/{city.city_max_hp()})")

    def _capture_city(self, unit, city) -> str:
        """Melee capture (M31): ownership flips, population drops, occupation."""
        old_owner = city.owner
        city.owner = unit.owner
        city.owner_id = unit.owner
        city.population = max(1, int(city.population * 0.75))
        city.hp = city.city_max_hp() // 2
        city.occupied_turns = 10
        unit.position = city.position
        return f"{city.name} has FALLEN! {unit.owner} seizes it from {old_owner}"
    
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
