"""All static game data: terrain, units, buildings, tech, traits, events, civilizations."""

import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set


# ── Terrain ──────────────────────────────────────────────────────────────────

class TerrainType(Enum):
    PLAINS = "Plains"
    GRASSLAND = "Grassland"
    FOREST = "Forest"
    HILLS = "Hills"
    MOUNTAIN = "Mountain"
    DESERT = "Desert"
    TUNDRA = "Tundra"
    WATER_COAST = "Coast"
    OCEAN = "Ocean"

TERRAIN_YIELDS = {
    TerrainType.PLAINS:       {"food": 2, "production": 1, "gold": 1, "science": 0},
    TerrainType.GRASSLAND:    {"food": 3, "production": 1, "gold": 1, "science": 0},
    TerrainType.FOREST:       {"food": 1, "production": 2, "gold": 0, "science": 1},
    TerrainType.HILLS:        {"food": 1, "production": 2, "gold": 1, "science": 0},
    TerrainType.MOUNTAIN:     {"food": 0, "production": 3, "gold": 2, "science": 1},
    TerrainType.DESERT:       {"food": 0, "production": 1, "gold": 1, "science": 0},
    TerrainType.TUNDRA:       {"food": 1, "production": 1, "gold": 0, "science": 0},
    TerrainType.WATER_COAST:  {"food": 2, "production": 0, "gold": 1, "science": 0},
    TerrainType.OCEAN:        {"food": 1, "production": 0, "gold": 0, "science": 0},
}

TERRAIN_MOVEMENT_COST = {
    TerrainType.PLAINS: 1, TerrainType.GRASSLAND: 1, TerrainType.HILLS: 2,
    TerrainType.FOREST: 2, TerrainType.MOUNTAIN: 99, TerrainType.DESERT: 2,
    TerrainType.TUNDRA: 2, TerrainType.WATER_COAST: 2, TerrainType.OCEAN: 3,
}

TERRAIN_DEFENSE_BONUS = {
    TerrainType.PLAINS: 0, TerrainType.GRASSLAND: 0, TerrainType.HILLS: 10,
    TerrainType.FOREST: 15, TerrainType.MOUNTAIN: 50, TerrainType.DESERT: 0,
    TerrainType.TUNDRA: 0, TerrainType.WATER_COAST: 0, TerrainType.OCEAN: 0,
}


# ── Resources ────────────────────────────────────────────────────────────────

class ResourceType(Enum):
    BONUS_WHEAT = ("Bonus", "Wheat", 2)
    BONUS_FISH = ("Bonus", "Fish", 2)
    BONUS_GAME = ("Bonus", "Game", 1)
    LUXURY_SILK = ("Luxury", "Silk", 2)
    LUXURY_SPICES = ("Luxury", "Spices", 3)
    LUXURY_IVORY = ("Luxury", "Ivory", 2)
    STRATEGIC_IRON = ("Strategic", "Iron", 3)
    STRATEGIC_HORSES = ("Strategic", "Horses", 3)
    STRATEGIC_OIL = ("Strategic", "Oil", 5)

    def __init__(self, category: str, display_name: str, quantity: int):
        self.category = category
        self.display_name = display_name
        self.quantity = quantity


# ── Phase 1.1: Map Resources & Terrain Depth ──────────────────────────────────

@dataclass
class ResourceYield:
    """Yields provided by a resource on a tile."""
    food: float = 0
    production: float = 0
    gold: float = 0
    science: float = 0
    faith: float = 0
    happiness: float = 0


@dataclass
class ResourceRequirements:
    """Terrain and adjacency requirements for a resource type."""
    compatible_terrains: List[TerrainType]
    requires_river_adjacency: bool = False
    requires_hill_adjacency: bool = False
    requires_mountain_adjacency: bool = False
    requires_coast_adjacency: bool = False


# Phase 1.1: Resource yields and requirements
RESOURCE_YIELDS = {
    ResourceType.BONUS_WHEAT: ResourceYield(food=2, gold=1),
    ResourceType.BONUS_FISH: ResourceYield(food=3, gold=2),
    ResourceType.BONUS_GAME: ResourceYield(food=2, gold=1),
    ResourceType.LUXURY_SILK: ResourceYield(gold=3, happiness=1),
    ResourceType.LUXURY_SPICES: ResourceYield(gold=4, happiness=2),
    ResourceType.LUXURY_IVORY: ResourceYield(gold=3, happiness=1),
    ResourceType.STRATEGIC_IRON: ResourceYield(production=1),
    ResourceType.STRATEGIC_HORSES: ResourceYield(production=1, gold=1),
    ResourceType.STRATEGIC_OIL: ResourceYield(gold=5, production=2),
}

RESOURCE_REQUIREMENTS = {
    ResourceType.BONUS_WHEAT: ResourceRequirements(
        compatible_terrains=[TerrainType.PLAINS, TerrainType.GRASSLAND],
        requires_river_adjacency=False
    ),
    ResourceType.BONUS_FISH: ResourceRequirements(
        compatible_terrains=[TerrainType.WATER_COAST, TerrainType.OCEAN],
        requires_coast_adjacency=True
    ),
    ResourceType.BONUS_GAME: ResourceRequirements(
        compatible_terrains=[TerrainType.FOREST, TerrainType.GRASSLAND, TerrainType.PLAINS],
        requires_hill_adjacency=False
    ),
    ResourceType.LUXURY_SILK: ResourceRequirements(
        compatible_terrains=[TerrainType.GRASSLAND, TerrainType.PLAINS],
        requires_hill_adjacency=False
    ),
    ResourceType.LUXURY_SPICES: ResourceRequirements(
        compatible_terrains=[TerrainType.DESERT, TerrainType.TUNDRA],
        requires_mountain_adjacency=True
    ),
    ResourceType.LUXURY_IVORY: ResourceRequirements(
        compatible_terrains=[TerrainType.FOREST, TerrainType.TUNDRA],
        requires_mountain_adjacency=True
    ),
    ResourceType.STRATEGIC_IRON: ResourceRequirements(
        compatible_terrains=[TerrainType.HILLS, TerrainType.MOUNTAIN, TerrainType.FOREST],
        requires_mountain_adjacency=False
    ),
    ResourceType.STRATEGIC_HORSES: ResourceRequirements(
        compatible_terrains=[TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.TUNDRA],
        requires_hill_adjacency=False
    ),
    ResourceType.STRATEGIC_OIL: ResourceRequirements(
        compatible_terrains=[TerrainType.DESERT, TerrainType.WATER_COAST],
        requires_coast_adjacency=False
    ),
}

# Terrain compatibility map: which resources can spawn on which terrain
TERRAIN_RESOURCE_COMPATIBILITY = {
    TerrainType.PLAINS: [ResourceType.BONUS_WHEAT, ResourceType.BONUS_GAME, ResourceType.STRATEGIC_HORSES, ResourceType.LUXURY_SILK],
    TerrainType.GRASSLAND: [ResourceType.BONUS_WHEAT, ResourceType.BONUS_GAME, ResourceType.LUXURY_SILK, ResourceType.STRATEGIC_HORSES],
    TerrainType.FOREST: [ResourceType.BONUS_GAME, ResourceType.LUXURY_IVORY, ResourceType.STRATEGIC_IRON],
    TerrainType.HILLS: [ResourceType.BONUS_GAME, ResourceType.STRATEGIC_IRON, ResourceType.LUXURY_SILK],
    TerrainType.MOUNTAIN: [ResourceType.STRATEGIC_IRON, ResourceType.LUXURY_IVORY, ResourceType.LUXURY_SPICES],
    TerrainType.DESERT: [ResourceType.LUXURY_SPICES, ResourceType.STRATEGIC_OIL, ResourceType.BONUS_WHEAT],
    TerrainType.TUNDRA: [ResourceType.BONUS_GAME, ResourceType.LUXURY_IVORY, ResourceType.LUXURY_SPICES, ResourceType.STRATEGIC_HORSES],
    TerrainType.WATER_COAST: [ResourceType.BONUS_FISH, ResourceType.STRATEGIC_OIL],
    TerrainType.OCEAN: [ResourceType.BONUS_FISH],
}

# ── River System ──

class RiverType(Enum):
    RIVER = "River"
    LAKE = "Lake"
    SWAMP = "Swamp"


@dataclass
class RiverFeature:
    """Represents a river feature on the map."""
    river_type: RiverType = RiverType.RIVER
    tiles: List[Tuple[int, int]] = field(default_factory=list)
    fertility_bonus: float = 0.5  # food bonus for adjacent tiles

    def adjacent_tiles(self, map_width: int, map_height: int) -> List[Tuple[int, int]]:
        """Get unique tiles adjacent to the river."""
        adjacent = []
        river_set = set(self.tiles)
        for x in range(map_width):
            for y in range(map_height):
                if (x, y) not in river_set:
                    for rx, ry in self.tiles:
                        if abs(x - rx) <= 1 and abs(y - ry) <= 1:
                            adjacent.append((x, y))
                            break
        return adjacent


class RiverNetwork:
    """Generates rivers flowing from mountains to water."""

    TERRAIN_HIERARCHY = [
        TerrainType.MOUNTAIN,
        TerrainType.HILLS,
        TerrainType.FOREST,
        TerrainType.PLAINS,
        TerrainType.GRASSLAND,
        TerrainType.DESERT,
        TerrainType.TUNDRA,
        TerrainType.WATER_COAST,
        TerrainType.OCEAN,
    ]

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.rivers: List[RiverFeature] = []

    def generate_rivers(self, tiles: Dict[Tuple[int, int], "HexTile"],
                        num_rivers: int = 4) -> List[RiverFeature]:
        """Generate rivers from mountains to water. Returns list of RiverFeatures."""
        self.rivers = []
        mountains = [(q, r) for (q, r), t in tiles.items()
                     if t.terrain == TerrainType.MOUNTAIN]
        water = {(q, r) for (q, r), t in tiles.items()
                 if t.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN)}

        for _ in range(min(num_rivers, len(mountains) // 2)):
            river = self._generate_single_river(mountains, water, tiles)
            if river and len(river.tiles) >= 3:
                self.rivers.append(river)

        return self.rivers

    def _generate_single_river(self, mountains: List[Tuple[int, int]],
                                water: Set[Tuple[int, int]],
                                tiles: Dict[Tuple[int, int], "HexTile"]) -> Optional[RiverFeature]:
        """Generate a single river path from mountain to water."""
        if not mountains:
            return None

        start = random.choice(mountains)
        path = [start]
        current = start
        visited = {start}

        while len(path) < max(8, self.width // 2):
            neighbors = self._get_neighbors(*current, tiles)
            # Prefer downhill: water < hills < mountain < plains/grass < desert/tundra < forest
            def flow_score(pos):
                terrain = tiles.get(pos)
                if not terrain:
                    return 999
                if pos in water:
                    return 0  # strongest pull toward water
                terrain_order = {
                    TerrainType.MOUNTAIN: 0, TerrainType.HILLS: 1,
                    TerrainType.PLAINS: 2, TerrainType.GRASSLAND: 2,
                    TerrainType.DESERT: 3, TerrainType.TUNDRA: 3,
                    TerrainType.FOREST: 4,
                    TerrainType.WATER_COAST: 5, TerrainType.OCEAN: 6,
                }
                return terrain_order.get(terrain.terrain, 5)

            valid = [(n, flow_score(n)) for n in neighbors if n not in visited]
            if not valid:
                break

            # Sort by flow score (prefer downhill) with some randomness
            valid.sort(key=lambda x: x[1] + random.random() * 0.5)
            current = valid[0][0]
            path.append(current)
            visited.add(current)

            if current in water:
                break

        if len(path) < 3:
            return None

        river = RiverFeature(river_type=RiverType.RIVER, tiles=path)

        # Mark river tiles on the map
        for pos in path:
            if pos in tiles:
                tile = tiles[pos]
                # Only place rivers on non-water tiles
                if tile.terrain != TerrainType.OCEAN:
                    tile.has_river = True

        return river

    def _get_neighbors(self, q: int, r: int,
                       tiles: Dict[Tuple[int, int], "HexTile"]) -> List[Tuple[int, int]]:
        """Get valid neighbors for river flow."""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
        neighbors = []
        for dq, dr in directions:
            nq, nr = q + dq, r + dr
            if (nq, nr) in tiles:
                neighbors.append((nq, nr))
        return neighbors


# Climate zone definitions
class ClimateZone(Enum):
    TEMPERATE = "Temperate"
    TROPICAL = "Tropical"
    ARID = "Arid"
    COLD = "Cold"
    POLAR = "Polar"


@dataclass
class ClimateModifier:
    """Effects applied by a climate zone."""
    food_multiplier: float = 1.0
    production_multiplier: float = 1.0
    gold_multiplier: float = 1.0
    science_multiplier: float = 1.0
    faith_multiplier: float = 1.0
    happiness_modifier: float = 0.0
    movement_modifier: float = 0.0  # percentage added to movement cost
    defense_bonus: float = 0.0
    disease_chance: float = 0.0
    water_penalty: float = 0.0


CLIMATE_MODIFIERS = {
    ClimateZone.TEMPERATE: ClimateModifier(
        food_multiplier=1.0, production_multiplier=1.0, gold_multiplier=1.0,
        science_multiplier=1.0, faith_multiplier=1.0, happiness_modifier=0.0,
        movement_modifier=0.0, defense_bonus=0.0, disease_chance=0.0, water_penalty=0.0,
    ),
    ClimateZone.TROPICAL: ClimateModifier(
        food_multiplier=1.2, production_multiplier=0.9, gold_multiplier=1.1,
        science_multiplier=1.0, faith_multiplier=1.0, happiness_modifier=-0.2,
        movement_modifier=0.0, defense_bonus=0.0, disease_chance=0.1, water_penalty=0.0,
    ),
    ClimateZone.ARID: ClimateModifier(
        food_multiplier=0.7, production_multiplier=1.1, gold_multiplier=1.0,
        science_multiplier=1.0, faith_multiplier=1.0, happiness_modifier=-0.1,
        movement_modifier=0.0, defense_bonus=0.0, disease_chance=0.0, water_penalty=0.3,
    ),
    ClimateZone.COLD: ClimateModifier(
        food_multiplier=0.8, production_multiplier=1.2, gold_multiplier=0.9,
        science_multiplier=1.0, faith_multiplier=1.0, happiness_modifier=-0.15,
        movement_modifier=0.5, defense_bonus=0.2, disease_chance=0.0, water_penalty=0.0,
    ),
    ClimateZone.POLAR: ClimateModifier(
        food_multiplier=0.5, production_multiplier=0.8, gold_multiplier=0.8,
        science_multiplier=1.0, faith_multiplier=1.0, happiness_modifier=-2.0,
        movement_modifier=0.5, defense_bonus=0.0, disease_chance=0.0, water_penalty=0.0,
    ),
}


def get_climate_for_row(row: int, map_height: int) -> ClimateZone:
    """Determine climate zone based on latitude (row position on map)."""
    latitude = row / map_height  # 0.0 (top/pole) to 1.0 (bottom/pole)
    if latitude < 0.15:
        return ClimateZone.POLAR
    elif latitude < 0.3:
        return ClimateZone.COLD
    elif latitude < 0.7:
        return ClimateZone.TEMPERATE
    elif latitude < 0.85:
        return ClimateZone.TROPICAL
    else:
        return ClimateZone.ARID


# Coastline bonus definitions
COASTLINE_BONUSES = {
    "naval_production": 0.2,  # 20% bonus for naval unit production on coast
    "trade_route_bonus": 2,   # +2 gold per trade route for coastal cities
    "fishing_bonus": 1,       # +1 food for coastal city centers
    "harbor_bonus": 3,        # +3 gold for cities with harbor district
}

# Landmarks & ruins data
class LandmarkType(Enum):
    RUINS = "Ruins"
    MONUMENT = "Monument"
    SHRINE = "Shrine"
    ANCIENT_WELL = "Ancient Well"
    BURIED_TREASURE = "Buried Treasure"
    ANCIENT_RUINS = "Ancient Ruins"
    BATTLEFIELD = "Battlefield"


@dataclass
class Landmark:
    """Represents a discoverable landmark on the map."""
    name: str
    landmark_type: LandmarkType
    food_bonus: float = 0
    production_bonus: float = 0
    gold_bonus: float = 0
    science_bonus: float = 0
    faith_bonus: float = 0
    happiness_bonus: float = 0
    discovery_reward: Optional[str] = None  # one-time bonus on discovery


LANDMARKS = {
    LandmarkType.RUINS: Landmark("Ruins", LandmarkType.RUINS, science_bonus=2),
    LandmarkType.MONUMENT: Landmark("Ancient Monument", LandmarkType.MONUMENT, gold_bonus=3, happiness_bonus=1),
    LandmarkType.SHRINE: Landmark("Ancient Shrine", LandmarkType.SHRINE, faith_bonus=3),
    LandmarkType.ANCIENT_WELL: Landmark("Ancient Well", LandmarkType.ANCIENT_WELL, food_bonus=2),
    LandmarkType.BURIED_TREASURE: Landmark("Buried Treasure", LandmarkType.BURIED_TREASURE, gold_bonus=50, discovery_reward="one_time_gold"),
    LandmarkType.ANCIENT_RUINS: Landmark("Ancient Ruins", LandmarkType.ANCIENT_RUINS, science_bonus=3, faith_bonus=2),
    LandmarkType.BATTLEFIELD: Landmark("Ancient Battlefield", LandmarkType.BATTLEFIELD, production_bonus=2, happiness_bonus=-1),
}


# ── Districts ────────────────────────────────────────────────────────────────

@dataclass
class DistrictType:
    name: str
    production_cost: int
    adjacency_bonus: Dict[str, float]  # {terrain_or_district_name: bonus}
    science_bonus: float
    gold_bonus: float
    faith_bonus: float
    happiness_bonus: float


DISTRICTS = {
    "Campus": DistrictType("Campus", 80, {"Mountain": 1.0, "Campus": 0.5}, 5.0, 0.0, 0.0, 0.0),
    "Commercial Hub": DistrictType("Commercial Hub", 80, {"River": 1.0, "Market": 0.5}, 1.0, 5.0, 0.0, 0.0),
    "Holy Site": DistrictType("Holy Site", 60, {"Hills": 0.5, "Shrine": 1.0}, 0.0, 1.0, 3.0, 0.0),
    "Encampment": DistrictType("Encampment", 80, {"Hills": 0.5}, 0.0, 0.0, 0.0, 0.0),
    "Harbor": DistrictType("Harbor", 70, {"Coast": 1.0}, 1.0, 4.0, 0.0, 1.0),
    "Entertainment": DistrictType("Entertainment", 90, {"Aqueduct": 0.5}, 0.0, 2.0, 0.0, 5.0),
    "Fortress": DistrictType("Fortress", 100, {}, 0.0, 0.0, 0.0, 0.0),
}


# ── Buildings ────────────────────────────────────────────────────────────────

@dataclass
class BuildingType:
    name: str
    district: str
    production_cost: int
    food: float = 0
    production: float = 0
    gold: float = 0
    science: float = 0
    faith: float = 0
    happiness: float = 0
    defense_bonus: int = 0
    requires_district: Optional[str] = None
    requires_tech: Optional[str] = None


BUILDINGS = {
    "Granary": BuildingType("Granary", "City Center", 60, food=3),
    "Market": BuildingType("Market", "Commercial Hub", 50, gold=3, requires_district="Commercial Hub"),
    "Bank": BuildingType("Bank", "Commercial Hub", 100, gold=5, requires_district="Commercial Hub", requires_tech="Coinage"),
    "Temple": BuildingType("Temple", "Holy Site", 50, faith=4, requires_district="Holy Site"),
    "Shrine": BuildingType("Shrine", "Holy Site", 25, faith=2, requires_district="Holy Site"),
    "Library": BuildingType("Library", "Campus", 50, science=3, requires_district="Campus"),
    "University": BuildingType("University", "Campus", 100, science=5, requires_district="Campus", requires_tech="Education"),
    "Barracks": BuildingType("Barracks", "Encampment", 40, defense_bonus=10, requires_district="Encampment"),
    "Stable": BuildingType("Stable", "Encampment", 60, production=2, requires_district="Encampment", requires_tech="Horsemanship"),
    "Lighthouse": BuildingType("Lighthouse", "Harbor", 60, science=2, gold=2, requires_district="Harbor"),
    "Aqueduct": BuildingType("Aqueduct", "City Center", 80, food=4, requires_tech="Engineering"),
    "Wall": BuildingType("Wall", "City Center", 60, defense_bonus=20, requires_district="City Center"),
    "Theater": BuildingType("Theater", "Entertainment", 60, happiness=3, gold=1, requires_district="Entertainment"),
    "Monument": BuildingType("Monument", "City Center", 30, science=1),
}


# ── Unit Types ───────────────────────────────────────────────────────────────

class UnitCategory(Enum):
    MELEE = "Melee"
    RANGED = "Ranged"
    CAVALRY = "Cavalry"
    SIEGE = "Siege"
    NAVAL = "Naval"
    SETTLER = "Settler"
    WORKER = "Worker"
    HELD = "Holy Order"


@dataclass
class UnitType:
    name: str
    category: UnitCategory
    attack: int
    defense: int
    movement: int
    production_cost: int
    gold_maintenance: int
    resource_required: Optional[str] = None
    requires_tech: Optional[str] = None
    unique_to: Optional[str] = None  # civilization name


UNIT_TYPES: Dict[str, UnitType] = {}
for _name, _args in [
    ("Militia",        (UnitCategory.MELEE, 5,  6,  1, 25,   0, None, None, None)),
    ("Swordsman",      (UnitCategory.MELEE, 10, 10, 1, 50,   1, "Iron", "Iron Working", None)),
    ("Legion",         (UnitCategory.MELEE, 13, 12, 1, 70,   1, "Iron", "Iron Working", "Rome")),
    ("Phalanx",        (UnitCategory.MELEE, 11, 14, 1, 55,   0, None, "Iron Working", "Greece")),
    ("Archer",         (UnitCategory.RANGED, 8,  5,  1, 40,   1, None, "Archery", None)),
    ("Crossbowman",    (UnitCategory.RANGED, 11, 6,  1, 60,   1, "Iron", "Iron Working", None)),
    ("Knight",         (UnitCategory.CAVALRY, 13, 10, 2, 80,   2, "Horses", "Chivalry", None)),
    ("Chariot",        (UnitCategory.CAVALRY, 12, 7,  2, 60,   1, "Horses", "Animal Husbandry", "Mesopotamia")),
    ("Siege Tower",    (UnitCategory.SIEGE, 14, 3,  1, 90,   2, None, "Engineering", None)),
    ("Catapult",       (UnitCategory.SIEGE, 16, 3,  1, 100,  2, None, "Engineering", None)),
    ("Trireme",        (UnitCategory.NAVAL, 9,  7,  3, 70,   1, None, "Mathematics", None)),
    ("Galley",         (UnitCategory.NAVAL, 7,  5,  3, 50,   0, None, "Navigation", None)),
    ("Settler",        (UnitCategory.SETTLER, 0,  0,  2, 100,  0, None, None, None)),
    ("Worker",         (UnitCategory.WORKER, 0,  0,  2, 40,   0, None, None, None)),
    ("Monk",           (UnitCategory.HELD,  4,  5,  2, 60,   0, None, "Theology", None)),
    ("Trader",         (UnitCategory.WORKER, 0,  0,  4, 50,   0, None, "Currency", None)),
]:
    UNIT_TYPES[_name] = UnitType(_name, *_args)


# ── Wonders ──────────────────────────────────────────────────────────────────

@dataclass
class WonderType:
    name: str
    era: Era
    cost: int
    effects: Dict[str, float]
    requires_tech: Optional[str] = None


WONDERS: Dict[str, WonderType] = {
    'Pyramids': WonderType('Pyramids', Era.ANCIENT, 220, {'worker_speed': 1.25}),
    'Great Library': WonderType('Great Library', Era.ANCIENT, 200, {'science_bonus': 0.1}),
    'Stonehenge': WonderType('Stonehenge', Era.ANCIENT, 180, {'faith_per_turn': 2}),
    'Colosseum': WonderType('Colosseum', Era.CLASSICAL, 300, {'happiness': 3}),
    'Oxford University': WonderType('Oxford University', Era.RENAISSANCE, 500, {'science_bonus': 0.2}),
}

# Set of wonder names already built by any civ (global uniqueness)
BUILT_WONDERS: Set[str] = set()


# ── Technology Tree ──────────────────────────────────────────────────────────

class TechBranch(Enum):
    SCIENTIFIC = "Scientific"
    MILITARY = "Military"
    CIVIC = "Civic"


class Era(Enum):
    ANCIENT = "Ancient"
    CLASSICAL = "Classical"
    MEDIEVAL = "Medieval"
    RENAISSANCE = "Renaissance"
    INDUSTRIAL = "Industrial"
    MODERN = "Modern"


@dataclass
class Technology:
    name: str
    branch: TechBranch
    era: Era
    cost: int
    prerequisites: List[str] = field(default_factory=list)
    unlocks: List[str] = field(default_factory=list)  # units, buildings, districts
    bonus: Optional[str] = None


TECHNOLOGIES = {
    # Ancient Era
    "Agriculture":      Technology("Agriculture", TechBranch.SCIENTIFIC, Era.ANCIENT, 20, [], ["Farm"], "+1 food to Farms"),
    "Mining":           Technology("Mining", TechBranch.SCIENTIFIC, Era.ANCIENT, 25, [], ["Mine"], "+1 production to Mines"),
    "Pottery":          Technology("Pottery", TechBranch.SCIENTIFIC, Era.ANCIENT, 15, [], None, "+1 gold to City Center"),
    "Archery":          Technology("Archery", TechBranch.MILITARY, Era.ANCIENT, 25, [], ["Archer"], "Unlocks Archer unit"),
    "Animal Husbandry": Technology("Animal Husbandry", TechBranch.SCIENTIFIC, Era.ANCIENT, 30, [], ["Pasture", "Chariot"], "+1 food to Pastures"),
    "Astronomy":        Technology("Astronomy", TechBranch.SCIENTIFIC, Era.ANCIENT, 20, [], None, "Coastal cities +1 science"),
    # Classical Era
    "Iron Working":     Technology("Iron Working", TechBranch.MILITARY, Era.CLASSICAL, 40, ["Mining"], ["Swordsman", "Crossbowman"], "+10% attack vs units"),
    "Masonry":          Technology("Masonry", TechBranch.SCIENTIFIC, Era.CLASSICAL, 35, ["Pottery"], ["Wall"], "Unlocks Walls"),
    "Philosophy":       Technology("Philosophy", TechBranch.CIVIC, Era.CLASSICAL, 50, ["Astronomy"], ["University"], "+2 science to Campus"),
    "Mathematics":      Technology("Mathematics", TechBranch.SCIENTIFIC, Era.CLASSICAL, 45, ["Astronomy"], ["Lighthouse", "Bridge"], "+1 movement to naval"),
    "Chivalry":         Technology("Chivalry", TechBranch.MILITARY, Era.CLASSICAL, 55, ["Iron Working"], ["Knight"], "Unlocks Knight unit"),
    "Coinage":          Technology("Coinage", TechBranch.CIVIC, Era.CLASSICAL, 35, ["Pottery"], ["Market", "Bank"], "Trade routes generate gold"),
    "Engineering":      Technology("Engineering", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 60, ["Masonry", "Mathematics"], ["Aqueduct", "Catapult"], "Cities +2 food"),
    "Education":        Technology("Education", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 70, ["Philosophy"], ["University"], "Campus +2 science"),
    "Feudalism":        Technology("Feudalism", TechBranch.CIVIC, Era.MEDIEVAL, 65, ["Chivalry", "Coinage"], ["Castle"], "Vassal tax bonus +10%"),
    "Theology":         Technology("Theology", TechBranch.CIVIC, Era.MEDIEVAL, 60, ["Philosophy"], ["Temple", "Monk"], "Unlocks Holy Orders"),
    "Rationalism":      Technology("Rationalism", TechBranch.CIVIC, Era.RENAISSANCE, 100, ["Education", "Theology"], ["Parliament"], "Capitalism unlocks"),
    "Printing Press":   Technology("Printing Press", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 90, ["Education"], ["Newspaper"], "+2 science to all cities"),
    "Gunpowder":        Technology("Gunpowder", TechBranch.MILITARY, Era.RENAISSANCE, 110, ["Engineering", "Feudalism"], ["Musketman"], "Unlocks Gunpowder units"),
    "Navigation":       Technology("Navigation", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 100, ["Mathematics"], ["Caravel"], "Unlocks Caravel naval unit"),
    "Steel":            Technology("Steel", TechBranch.MILITARY, Era.INDUSTRIAL, 130, ["Gunpowder", "Feudalism"], ["Ironclad"], "Unlocks Steel units"),
    "Classicism":       Technology("Classicism", TechBranch.CIVIC, Era.INDUSTRIAL, 120, ["Rationalism"], ["Opera House"], "+2 happiness per Theater"),
    "Military Science": Technology("Military Science", TechBranch.MILITARY, Era.MODERN, 150, ["Steel"], ["Rifleman"], "Unlocks Rifleman unit"),
    "Ballistics":       Technology("Ballistics", TechBranch.MILITARY, Era.MODERN, 160, ["Military Science"], ["Cannon"], "Unlocks Cannon unit"),
    "Flight":           Technology("Flight", TechBranch.SCIENTIFIC, Era.MODERN, 200, ["Steel", "Classicism"], ["Airplane"], "Unlocks Airplane unit"),
}


# ── Government Types ─────────────────────────────────────────────────────────

@dataclass
class Government:
    name: str
    bonus: str
    policy_slots: int
    stability_mod: float


GOVERNMENTS = {
    "Monarchy":     Government("Monarchy", "+10% legitimacy for each allied civ", 3, 1.0),
    "Republic":     Government("Republic", "+1 science per policy slot", 3, 0.9),
    "Theocracy":    Government("Theocracy", "+2 faith per Holy Site", 2, 0.95),
    "Feudalism":    Government("Feudalism", "+15% military power", 3, 1.1),
    "Oligarchy":    Government("Oligarchy", "+1 gold per Commercial Hub", 2, 0.95),
    "Custom":       Government("Custom", "No bonuses", 0, 1.0),
}


# ── Succession Laws ──────────────────────────────────────────────────────────

class SuccessionLaw(Enum):
    PRIMAGENITURE = "Primogeniture"
    ULTOGENITURE = "Ultogeniture"
    GAVELKIND = "Gavelkind"
    SENIORITY = "Seniority"
    COGNATIC = "Cognatic"
    ELECTIVE = "Elective"


# ── Traits Database ──────────────────────────────────────────────────────────

TRAIT_DATABASE = {
    # Positive traits
    "Industrious":     {"stewardship": 2},
    "Brave":           {"martial": 2},
    "Charismatic":     {"diplomacy": 2},
    "Cunning":         {"intrigue": 2},
    "Scholar":         {"science": 2},
    "Warrior":         {"martial": 3},
    "Diplomat":        {"diplomacy": 3},
    "Spymaster":       {"intrigue": 3},
    "Just":            {"stewardship": 1, "diplomacy": 1},
    "Tyrannical":      {"martial": 1, "diplomacy": -2},
    "Gregarious":      {"diplomacy": 1, "stewardship": 1},
    "Opportunistic":   {"intrigue": 1, "martial": 1},
    "Ascetic":         {"science": 1, "faith": 2},
    "Magnanimous":     {"diplomacy": 2, "stewardship": 1},
    "Vengeful":        {"martial": 2, "diplomacy": -1},
    "Paranoid":        {"intrigue": 1, "diplomacy": -1},
    "Fickle":          {"diplomacy": -1, "stewardship": -1},
    # Negative traits
    "Cruel":           {"martial": 1, "diplomacy": -3, "happiness": -2},
    "Greedy":          {"gold": 2, "diplomacy": -2},
    "Gluttonous":      {"stewardship": -2, "martial": -1},
    "Chaste":          {"faith": 2, "diplomacy": -1},
    "Generous":        {"diplomacy": 1, "gold": -1},
}


# ── Civilizations ────────────────────────────────────────────────────────────

@dataclass
class Civilization:
    name: str
    unique_unit: str
    unique_building: str
    bonus: str
    preferred_gov: str
    starting_tech: List[str] = field(default_factory=list)
    color: str = "white"
    starting_gold: int = 100
    starting_science: int = 50
    starting_culture: int = 25
    starting_stats: Dict[str, int] = field(default_factory=lambda: {
        "diplomacy": 10, "martial": 10, "stewardship": 10, "intrigue": 10
    })
    starting_traits: List[str] = field(default_factory=lambda: ["Charismatic", "Warrior"])


CIVILIZATIONS = {
    "Rome": Civilization("Rome", "Legion", "Wall", "+10% melee combat strength", "Republic", ["Iron Working", "Masonry"], "white", 100, 50, 25, {"diplomacy": 10, "martial": 12, "stewardship": 10, "intrigue": 8}, ["Warrior", "Industrious"]),
    "Greece": Civilization("Greece", "Phalanx", "", "+1 science from all tiles", "Republic", ["Philosophy", "Pottery"], "lightblue", 80, 80, 30, {"diplomacy": 12, "martial": 10, "stewardship": 8, "intrigue": 10}, ["Scholar", "Charismatic"]),
    "Mesopotamia": Civilization("Mesopotamia", "Chariot", "", "+1 food from Plains tiles", "Monarchy", ["Agriculture", "Animal Husbandry"], "#f5deb3", 120, 40, 20, {"diplomacy": 10, "martial": 11, "stewardship": 12, "intrigue": 7}, ["Industrious", "Diplomat"]),
    "Egypt": Civilization("Egypt", "", "Pyramid", "Wonders cost 20% less", "Theocracy", ["Astronomy", "Masonry"], "#ffd700", 90, 60, 40, {"diplomacy": 11, "martial": 10, "stewardship": 9, "intrigue": 10}, ["Charismatic", "Magnanimous"]),
    "Persia": Civilization("Persia", "", "Satrap", "+1 gold from every resource", "Monarchy", ["Coinage", "Feudalism"], "#800080", 110, 50, 30, {"diplomacy": 12, "martial": 9, "stewardship": 11, "intrigue": 8}, ["Diplomat", "Cunning"]),
    "China": Civilization("China", "", "Gunpowder", "+1 science from every tile", "Republic", ["Education", "Printing Press"], "red", 85, 85, 35, {"diplomacy": 10, "martial": 9, "stewardship": 11, "intrigue": 10}, ["Scholar", "Just"]),
    "Mongol": Civilization("Mongol", "", "", "+2 movement for cavalry units", "Custom", ["Animal Husbandry", "Chivalry"], "#a52a2a", 70, 30, 15, {"diplomacy": 8, "martial": 14, "stewardship": 7, "intrigue": 11}, ["Warrior", "Brave"]),
    "Viking": Civilization("Viking", "", "Longhouse", "Coastal tiles provide +1 production", "Custom", ["Navigation", "Astronomy"], "#c0c0c0", 95, 45, 20, {"diplomacy": 9, "martial": 13, "stewardship": 8, "intrigue": 10}, ["Warrior", "Opportunistic"]),
    "India": Civilization("India", "", "", "+1 faith from all tiles", "Theocracy", ["Theology", "Philosophy"], "#ff9933", 100, 60, 50, {"diplomacy": 12, "martial": 8, "stewardship": 11, "intrigue": 9}, ["Charismatic", "Magnanimous"]),
    "Byzantium": Civilization("Byzantium", "", "Hypodrome", "+1 gold and +1 science from cities", "Oligarchy", ["Mathematics", "Coinage"], "#000080", 115, 70, 35, {"diplomacy": 11, "martial": 10, "stewardship": 12, "intrigue": 7}, ["Scholar", "Diplomat"]),
    "England": Civilization("England", "", "Longbowman", "Ranged units have +2 attack", "Monarchy", ["Archery", "Chivalry"], "green", 90, 55, 30, {"diplomacy": 11, "martial": 11, "stewardship": 9, "intrigue": 9}, ["Warrior", "Charismatic"]),
    "Ottoman": Civilization("Ottoman", "", "Janissary", "Gunpowder units cost 20% less", "Theocracy", ["Gunpowder", "Feudalism"], "teal", 105, 45, 25, {"diplomacy": 10, "martial": 12, "stewardship": 10, "intrigue": 8}, ["Warrior", "Industrious"]),
}


# ── Unit Promotions ──────────────────────────────────────────────────────────

PROMOTION_TIERS = {
    "Veteran":   {"attack": 2, "defense": 2, "requires_xp": 3},
    "Elite":     {"attack": 4, "defense": 4, "requires_xp": 8},
    "Champion":  {"attack": 6, "defense": 6, "requires_xp": 15},
}


# ── Religion Types ───────────────────────────────────────────────────────────

@dataclass
class Doctrine:
    name: str
    faith_bonus: float
    happiness_bonus: float
    gold_bonus: float
    description: str


DOCTRINES = {
    "Monotheism":      Doctrine("Monotheism", 3.0, 2.0, 1.0, "Single god, strong faith and happiness"),
    "Polytheism":      Doctrine("Polytheism", 1.0, 3.0, 2.0, "Many gods, strong happiness and gold"),
    "Pantheon":        Doctrine("Pantheon", 2.0, 1.0, 0.5, "Nature spirits, balanced bonuses"),
    "Animism":         Doctrine("Animism", 1.5, 1.5, 1.0, "Spirit of all things, moderate all-around"),
}


# ── Court Positions ──────────────────────────────────────────────────────────

COURT_POSITIONS = {
    "Marshal":     {"bonus_stat": "martial", "bonus_amount": 0.15, "description": "+15% military power"},
    "Spymaster":   {"bonus_stat": "intrigue", "bonus_amount": 0.20, "description": "+20% plot detection"},
    "Chancellor":  {"bonus_stat": "diplomacy", "bonus_amount": 0.15, "description": "+15% gold from trade"},
    "Steward":     {"bonus_stat": "stewardship", "bonus_amount": 0.15, "description": "+15% economy"},
    "Chaplain":    {"bonus_stat": "faith", "bonus_amount": 2.0, "description": "+2 faith per turn"},
}


# ── Event Categories ─────────────────────────────────────────────────────────

class EventCategory(Enum):
    CHARACTER = "Character"
    CITY = "City"
    WORLD = "World"
    DIPLOMATIC = "Diplomatic"
    MILITARY = "Military"
    RELIGIOUS = "Religious"


# ── Victory Conditions ───────────────────────────────────────────────────────

VICTORY_CONDITIONS = {
    "Domination": {"type": "control", "value": 0.5, "description": "Control 50% of starting cities"},
    "Science":    {"type": "era", "value": Era.MODERN, "description": "Reach Modern Era"},
    "Culture":    {"type": "culture", "value": 1000, "description": "Accumulate 1000 culture points"},
    "Diplomacy":  {"type": "alliance", "value": 5, "description": "Have 5 allied civilizations"},
    "Dynasty":    {"type": "generations", "value": 10, "description": "Survive 10 generations"},
}


# ── Map Generation Parameters ────────────────────────────────────────────────

MAP_WEIGHTS = {
    TerrainType.PLAINS: 0.3,
    TerrainType.GRASSLAND: 0.25,
    TerrainType.FOREST: 0.15,
    TerrainType.HILLS: 0.1,
    TerrainType.MOUNTAIN: 0.05,
    TerrainType.DESERT: 0.05,
    TerrainType.TUNDRA: 0.03,
    TerrainType.WATER_COAST: 0.04,
    TerrainType.OCEAN: 0.03,
}

RESOURCE_WEIGHTS = {
    ResourceType.BONUS_WHEAT: 0.15,
    ResourceType.BONUS_FISH: 0.10,
    ResourceType.BONUS_GAME: 0.10,
    ResourceType.LUXURY_SILK: 0.03,
    ResourceType.LUXURY_SPICES: 0.02,
    ResourceType.LUXURY_IVORY: 0.02,
    ResourceType.STRATEGIC_IRON: 0.04,
    ResourceType.STRATEGIC_HORSES: 0.04,
    ResourceType.STRATEGIC_OIL: 0.01,
}
