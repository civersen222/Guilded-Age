"""
CivKings - Unit System Enhancement
Handles unit upgrades, production queues, naval/siege units, stacking rules, and experience.
"""
from typing import List, Dict, Optional, Tuple
from game_data import UNIT_TYPES, UnitCategory, UnitType, Technology


# ── Unit Upgrade Chains ──

UNIT_UPGRADE_CHAINS = {
    "Militia": "Swordsman",
    "Archer": "Crossbowman",
    "Trireme": "Ship of the Line",
    "Galley": "Frigate",
    "Settler": None,  # No upgrades
    "Worker": None,
    "Monk": None,
}

# Additional upgrades beyond what's in UNIT_TYPES
ADDITIONAL_UNIT_TYPES = {
    "Swordsman": UnitType("Swordsman", UnitCategory.MELEE, 10, 10, 1, 50, 1, "Iron", None),
    "Crossbowman": UnitType("Crossbowman", UnitCategory.RANGED, 11, 6, 1, 60, 1, "Iron", None),
    "Ship of the Line": UnitType("Ship of the Line", UnitCategory.NAVAL, 15, 10, 3, 120, 2, "Strategic_Oil", None),
    "Frigate": UnitType("Frigate", UnitCategory.NAVAL, 12, 8, 3, 90, 2, None, None),
    "Trebuchet": UnitType("Trebuchet", UnitCategory.SIEGE, 18, 4, 1, 130, 2, None, None),
    "Infantry": UnitType("Infantry", UnitCategory.MELEE, 15, 12, 1, 80, 2, "Strategic_Oil", None),
    "Ranger": UnitType("Ranger", UnitCategory.RANGED, 14, 8, 2, 90, 1, None, None),
}

# Merge into global UNIT_TYPES
UNIT_TYPES.update(ADDITIONAL_UNIT_TYPES)


# ── Unit Production Queue ──

class ProductionItem:
    """An item queued for production in a city."""
    
    def __init__(self, item_type: str, item_name: str, cost: int, turns_remaining: int):
        self.item_type = item_type  # "unit", "building", "district"
        self.item_name = item_name
        self.cost = cost
        self.turns_remaining = turns_remaining
    
    def __repr__(self):
        return f"ProductionItem({self.item_type}, {self.item_name}, {self.cost})"


# ── Naval Unit Enhancements ──

NAVAL_UNIT_BONUSES = {
    "Coastal_Adjacency": {"attack": 2, "defense": 2},
    "Ocean_Range": {"movement": 1},
    "Trade_Raiding": {"gold_bonus": 5},
}

# Naval units get +2 attack/defense when on water tiles
def apply_naval_bonus(unit) -> bool:
    """Check if unit is a naval unit and apply terrain bonuses."""
    if unit.unit_type in ADDITIONAL_UNIT_TYPES:
        utype = ADDITIONAL_UNIT_TYPES[unit.unit_type]
        if utype.category == UnitCategory.NAVAL:
            return True
    return False


# ── Siege Unit Enhancements ──

SIEGE_ATTACK_BONUSES = {
    "vs_Walls": 50,  # +50% attack vs fortified/walled targets
    "vs_Cities": 25,  # +25% attack vs city defenses
    "vs_Fortress": 30,  # +30% attack vs fortress
}

def calculate_siege_bonus(unit, target) -> float:
    """Calculate siege attack bonus against a target."""
    bonus = 1.0
    
    if hasattr(target, 'has_wall') and target.has_wall:
        bonus += SIEGE_ATTACK_BONUSES["vs_Walls"] / 100.0
    if hasattr(target, 'is_city') and target.is_city:
        bonus += SIEGE_ATTACK_BONUSES["vs_Cities"] / 100.0
    if hasattr(target, 'is_fortress') and target.is_fortress:
        bonus += SIEGE_ATTACK_BONUSES["vs_Fortress"] / 100.0
    
    return bonus


# ── Unit Stacking Rules ──

class UnitStack:
    """Manages multiple units on a single tile."""
    
    MAX_STACK_SIZE = 4  # Maximum units per tile
    MAX_MILITARY_STACK = 3  # Maximum military units per tile
    
    def __init__(self):
        self.units: List = []
    
    def can_add_unit(self, unit) -> Tuple[bool, str]:
        """Check if a unit can be added to the stack."""
        if len(self.units) >= UnitStack.MAX_STACK_SIZE:
            return False, "Stack full"
        
        if unit.unit_type in UNIT_TYPES:
            utype = UNIT_TYPES[unit.unit_type]
            if utype.category not in (UnitCategory.SETTLER, UnitCategory.WORKER):
                military_count = sum(1 for u in self.units 
                                   if u.unit_type in UNIT_TYPES 
                                   and UNIT_TYPES[u.unit_type].category != UnitCategory.SETTLER
                                   and UNIT_TYPES[u.unit_type].category != UnitCategory.WORKER)
                if military_count >= UnitStack.MAX_MILITARY_STACK:
                    return False, "Too many military units"
        
        # Check for friendly units
        friendly_count = sum(1 for u in self.units if u.owner == unit.owner)
        if friendly_count >= UnitStack.MAX_STACK_SIZE - 1:
            return False, "Too many friendly units"
        
        return True, "OK"
    
    def add_unit(self, unit) -> bool:
        """Add a unit to the stack."""
        can_add, _ = self.can_add_unit(unit)
        if can_add:
            self.units.append(unit)
            return True
        return False
    
    def remove_unit(self, unit) -> bool:
        """Remove a unit from the stack."""
        if unit in self.units:
            self.units.remove(unit)
            return True
        return False
    
    def get_total_attack(self) -> int:
        """Calculate total attack power of the stack."""
        return sum(u.attack for u in self.units if u.is_alive)
    
    def get_total_defense(self) -> int:
        """Calculate total defense power of the stack."""
        return sum(u.defense for u in self.units if u.is_alive)
    
    def get_active_units(self) -> List:
        """Get all active units in the stack."""
        return [u for u in self.units if u.is_alive]
    
    def get_military_units(self) -> List:
        """Get all military units in the stack."""
        military = []
        for u in self.units:
            if u.unit_type in UNIT_TYPES:
                utype = UNIT_TYPES[u.unit_type]
                if utype.category not in (UnitCategory.SETTLER, UnitCategory.WORKER):
                    military.append(u)
        return military


# ── Unit Experience System Enhancement ──

class ExperienceManager:
    """Manages unit experience and promotions."""
    
    PROMOTION_TIERS = [
        (50, "Novice", {"attack": 5}),
        (150, "Skilled", {"defense": 10}),
        (300, "Veteran", {"movement": 1}),
        (500, "Elite", {"attack": 15}),
        (750, "Champion", {"defense": 20}),
        (1000, "Grand Champion", {"attack": 10, "defense": 10}),
    ]
    
    @staticmethod
    def gain_xp(unit, amount: int) -> List[str]:
        """Gain XP and return list of new promotions."""
        unit.xp += amount
        new_promotions = []
        
        for xp_thresh, label, bonuses in ExperienceManager.PROMOTION_TIERS:
            if xp_thresh <= unit.xp and xp_thresh not in unit.promotions:
                unit.promotions.append(xp_thresh)
                new_promotions.append(label)
                
                # Apply bonuses
                for stat, val in bonuses.items():
                    if stat == "attack":
                        unit.attack += val
                    elif stat == "defense":
                        unit.defense += val
                    elif stat == "movement":
                        unit.max_moves += val
        
        if new_promotions:
            unit.level = len(unit.promotions) + 1
        
        return new_promotions
    
    @staticmethod
    def get_promotion_info(unit) -> Dict:
        """Get detailed promotion information for a unit."""
        current_xp = unit.xp
        next_promotion = None
        
        for xp_thresh, label, _ in ExperienceManager.PROMOTION_TIERS:
            if xp_thresh > current_xp:
                next_promotion = {"threshold": xp_thresh, "label": label}
                break
        
        return {
            "current_xp": current_xp,
            "next_promotion": next_promotion,
            "promotions": unit.promotions,
            "level": unit.level,
        }


# ── Unit Production Queue Manager ──

class ProductionQueueManager:
    """Manages unit and building production queues for cities."""
    
    def __init__(self):
        self.queues: Dict[str, List[ProductionItem]] = {}  # city_name -> queue
    
    def add_to_queue(self, city_name: str, item_type: str, item_name: str, cost: int, turns: int) -> bool:
        """Add an item to the production queue."""
        if city_name not in self.queues:
            self.queues[city_name] = []
        
        # Check if item is already at front of queue
        if self.queues[city_name] and self.queues[city_name][0].item_name == item_name:
            return False
        
        self.queues[city_name].append(ProductionItem(item_type, item_name, cost, turns))
        return True
    
    def process_queue(self, city_name: str, production: float) -> Optional[str]:
        """Process production queue and return completed item if any."""
        if city_name not in self.queues or not self.queues[city_name]:
            return None
        
        queue = self.queues[city_name]
        current_item = queue[0]
        
        # Complete the item
        current_item.cost -= production
        current_item.turns_remaining -= 1
        
        if current_item.cost <= 0:
            # Item completed
            completed = queue.pop(0)
            
            # Create the unit/building
            if completed.item_type == "unit":
                # Return unit data instead of creating unit object
                return {"type": "unit", "name": completed.item_name}
            elif completed.item_type == "building":
                return {"type": "building", "name": completed.item_name}
        
        return None
    
    def get_queue_status(self, city_name: str) -> List[Dict]:
        """Get status of production queue."""
        if city_name not in self.queues:
            return []
        
        return [
            {
                "item_type": item.item_type,
                "item_name": item.item_name,
                "cost_remaining": item.cost,
                "turns_remaining": item.turns_remaining,
            }
            for item in self.queues[city_name]
        ]
    
    def cancel_production(self, city_name: str) -> bool:
        """Cancel current production."""
        if city_name in self.queues and self.queues[city_name]:
            self.queues[city_name].pop(0)
            return True
        return False


# ── Unit Upgrade System ──

class UnitUpgradeManager:
    """Manages unit upgrades."""
    
    UPGRADE_COSTS = {
        "Militia": 25,
        "Swordsman": 50,
        "Archer": 40,
        "Crossbowman": 60,
        "Trireme": 70,
        "Ship of the Line": 120,
        "Galley": 50,
        "Frigate": 90,
    }
    
    @staticmethod
    def get_upgrade(unit) -> Optional[str]:
        """Get the next upgrade for a unit."""
        if unit.unit_type in UNIT_UPGRADE_CHAINS:
            return UNIT_UPGRADE_CHAINS[unit.unit_type]
        return None
    
    @staticmethod
    def can_upgrade(unit) -> Tuple[bool, str]:
        """Check if a unit can be upgraded."""
        upgrade = UnitUpgradeManager.get_upgrade(unit)
        if not upgrade:
            return False, "No upgrades available"
        
        if upgrade not in UNIT_TYPES:
            return False, "Upgrade not available"
        
        upgrade_type = UNIT_TYPES[upgrade]
        if upgrade_type.resource_required:
            # Check if player has the required resource
            if not hasattr(unit, 'owner') or not hasattr(unit.owner, 'resources'):
                return False, "Resource requirement not met"
        
        return True, f"Can upgrade to {upgrade}"
    
    @staticmethod
    def upgrade_unit(unit, player) -> Tuple[bool, str]:
        """Upgrade a unit."""
        can_upgrade, msg = UnitUpgradeManager.can_upgrade(unit)
        if not can_upgrade:
            return False, msg
        
        upgrade = UnitUpgradeManager.get_upgrade(unit)
        cost = UnitUpgradeManager.UPGRADE_COSTS.get(unit.unit_type, 50)
        
        if player.gold < cost:
            return False, "Not enough gold"
        
        # Perform upgrade
        player.gold -= cost
        unit.unit_type = upgrade
        utype = UNIT_TYPES[upgrade]
        unit.attack = utype.attack
        unit.defense = utype.defense
        unit.max_moves = utype.movement
        unit.max_hp = 100
        unit.hp = 100
        
        return True, f"Upgraded to {upgrade}"


# ── Main Unit Enhancement System ──

class UnitEnhancementSystem:
    """Main system for unit enhancements."""
    
    def __init__(self):
        self.experience_manager = ExperienceManager()
        self.production_queue = ProductionQueueManager()
        self.upgrade_manager = UnitUpgradeManager()
    
    def process_unit_combat(self, attacker, defender) -> Dict:
        """Process combat between two units with enhancements."""
        result = {
            "attacker_hp": attacker.hp,
            "defender_hp": defender.hp,
            "attacker_damaged": 0,
            "defender_damaged": 0,
            "winner": None,
        }
        
        # Calculate attack power
        atk_power = attacker.attack
        
        # Apply naval bonuses if applicable
        if apply_naval_bonus(attacker):
            # Check if attacker is on water
            if hasattr(attacker, 'position') and hasattr(attacker.position, 'terrain'):
                if attacker.position.terrain in ["Water", "Coast"]:
                    atk_power += NAVAL_UNIT_BONUSES["Coastal_Adjacency"]["attack"]
        
        # Apply siege bonuses if attacker is siege unit
        if attacker.unit_type in UNIT_TYPES:
            utype = UNIT_TYPES[attacker.unit_type]
            if utype.category == UnitCategory.SIEGE:
                atk_power *= calculate_siege_bonus(attacker, defender)
        
        # Calculate defense power
        def_power = defender.defense
        
        # Apply naval defense bonuses
        if apply_naval_bonus(defender):
            if hasattr(defender, 'position') and hasattr(defender.position, 'terrain'):
                if defender.position.terrain in ["Water", "Coast"]:
                    def_power += NAVAL_UNIT_BONUSES["Coastal_Adjacency"]["defense"]
        
        # Randomness
        import random
        atk_power += random.randint(-5, 5)
        def_power += random.randint(-5, 5)
        
        # Determine winner
        if atk_power > def_power:
            damage = max(1, atk_power - def_power)
            defender.hp -= damage
            result["defender_damaged"] = damage
            
            if defender.hp <= 0:
                defender.hp = 0
                defender.is_alive = False
                result["winner"] = "attacker"
        else:
            damage = max(1, def_power - atk_power)
            attacker.hp -= damage
            result["attacker_damaged"] = damage
            
            if attacker.hp <= 0:
                attacker.hp = 0
                attacker.is_alive = False
                result["winner"] = "defender"
        
        result["attacker_hp"] = attacker.hp
        result["defender_hp"] = defender.hp
        
        return result
    
    def start_production(self, city_name: str, item_type: str, item_name: str) -> bool:
        """Start production of a unit or building in a city."""
        cost = 0
        turns = 0
        
        if item_type == "unit":
            if item_name in UNIT_TYPES:
                utype = UNIT_TYPES[item_name]
                cost = utype.production_cost
                # Estimate turns based on city production
                turns = max(1, cost // 10)  # Simple estimation
            else:
                return False
        elif item_type == "building":
            # Building costs would come from city data
            cost = 50
            turns = max(1, cost // 10)
        else:
            return False
        
        return self.production_queue.add_to_queue(city_name, item_type, item_name, cost, turns)
    
    def process_city_production(self, city_name: str, production: float) -> Optional[Dict]:
        """Process city production and return completed item."""
        return self.production_queue.process_queue(city_name, production)

