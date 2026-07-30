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
    culture: float = 0
    happiness: float = 0
    defense_bonus: int = 0
    # Deep-systems spec 1.10: multiplicative yields, housing, upkeep
    production_pct: float = 0
    gold_pct: float = 0
    science_pct: float = 0
    housing: float = 0
    gold_maintenance: int = 0
    requires_district: Optional[str] = None
    requires_tech: Optional[str] = None


BUILDINGS = {
    "Granary": BuildingType("Granary", "City Center", 60, food=2, housing=2, gold_maintenance=1, requires_tech="Canning"),
    "Market": BuildingType("Market", "Commercial Hub", 50, gold_pct=0.25, requires_district="Commercial Hub", requires_tech="Commodity Exchanges"),
    "Bank": BuildingType("Bank", "Commercial Hub", 100, gold_pct=0.25, gold_maintenance=2, requires_district="Commercial Hub", requires_tech="Central Banking"),
    "Temple": BuildingType("Temple", "Holy Site", 50, faith=2, happiness=2, gold_maintenance=1, requires_district="Holy Site", requires_tech="Civil Institutions"),
    "Shrine": BuildingType("Shrine", "Holy Site", 25, faith=2, requires_district="Holy Site"),
    "Library": BuildingType("Library", "Campus", 50, science_pct=0.25, gold_maintenance=1, requires_district="Campus", requires_tech="Learned Societies"),
    "University": BuildingType("University", "Campus", 100, science_pct=0.33, gold_maintenance=2, requires_district="Campus", requires_tech="Mass Schooling"),
    "Barracks": BuildingType("Barracks", "Encampment", 40, defense_bonus=10, requires_district="Encampment"),
    "Stable": BuildingType("Stable", "Encampment", 60, production=2, requires_district="Encampment", requires_tech="Cavalry Doctrine"),
    "Lighthouse": BuildingType("Lighthouse", "Harbor", 60, science=2, gold=2, requires_district="Harbor"),
    "Aqueduct": BuildingType("Aqueduct", "City Center", 80, housing=4, gold_maintenance=1, requires_tech="Urban Sanitation"),
    "Wall": BuildingType("Wall", "City Center", 60, defense_bonus=20, requires_district="City Center"),
    "Theater": BuildingType("Theater", "Entertainment", 60, happiness=3, gold=1, gold_maintenance=1, requires_district="Entertainment"),
    "Monument": BuildingType("Monument", "City Center", 30, culture=2),
    "Workshop": BuildingType("Workshop", "City Center", 50, production_pct=0.25, gold_maintenance=1, requires_tech="Bessemer Process"),
    "Factory": BuildingType("Factory", "Industrial", 180, production_pct=0.50, gold_maintenance=3, requires_tech="Mass Production"),
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
    ("Swordsman",      (UnitCategory.MELEE, 10, 10, 1, 50,   1, "Iron", "Bessemer Process", None)),
    ("Legion",         (UnitCategory.MELEE, 13, 12, 1, 70,   1, "Iron", "Bessemer Process", "Rome")),
    ("Phalanx",        (UnitCategory.MELEE, 11, 14, 1, 55,   0, None, "Bessemer Process", "Greece")),
    ("Archer",         (UnitCategory.RANGED, 8,  5,  1, 40,   1, None, "Small Arms", None)),
    ("Crossbowman",    (UnitCategory.RANGED, 11, 6,  1, 60,   1, "Iron", "Bessemer Process", None)),
    ("Knight",         (UnitCategory.CAVALRY, 13, 10, 2, 80,   2, "Horses", "Cavalry Doctrine", None)),
    ("Chariot",        (UnitCategory.CAVALRY, 12, 7,  2, 60,   1, "Horses", "Stockyards", "Mesopotamia")),
    ("Siege Tower",    (UnitCategory.SIEGE, 14, 3,  1, 90,   2, None, "Heavy Artillery", None)),
    ("Catapult",       (UnitCategory.SIEGE, 16, 3,  1, 100,  2, None, "Heavy Artillery", None)),
    ("Trireme",        (UnitCategory.NAVAL, 9,  7,  3, 70,   1, None, "Marine Engineering", None)),
    ("Galley",         (UnitCategory.NAVAL, 7,  5,  3, 50,   0, None, "Steel Navies", None)),
    ("Settler",        (UnitCategory.SETTLER, 0,  0,  2, 100,  0, None, None, None)),
    ("Worker",         (UnitCategory.WORKER, 0,  0,  2, 40,   0, None, None, None)),
    ("Monk",           (UnitCategory.HELD,  4,  5,  2, 60,   0, None, "Civil Institutions", None)),
    ("Trader",         (UnitCategory.WORKER, 0,  0,  4, 50,   0, None, "Commodity Exchanges", None)),
]:
    UNIT_TYPES[_name] = UnitType(_name, *_args)


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
    # ── Age of Steam (Era.ANCIENT) ──
    "Steam Power":         Technology("Steam Power", TechBranch.SCIENTIFIC, Era.ANCIENT, 20, [], ["Rail Networks"], "+1 production to Mines"),
    "Mechanized Farming":  Technology("Mechanized Farming", TechBranch.SCIENTIFIC, Era.ANCIENT, 20, [], ["Farm"], "+1 food to Farms"),
    "Deep Mining":         Technology("Deep Mining", TechBranch.SCIENTIFIC, Era.ANCIENT, 25, [], ["Mine"], "+1 production to Mines"),
    "Canning":             Technology("Canning", TechBranch.SCIENTIFIC, Era.ANCIENT, 15, [], ["Granary"], "+1 gold to City Center"),
    "Small Arms":          Technology("Small Arms", TechBranch.MILITARY, Era.ANCIENT, 25, [], ["Archer"], "Unlocks rifle infantry"),
    "Stockyards":          Technology("Stockyards", TechBranch.SCIENTIFIC, Era.ANCIENT, 30, [], ["Pasture", "Chariot"], "+1 food to Pastures"),
    "Learned Societies":   Technology("Learned Societies", TechBranch.CIVIC, Era.ANCIENT, 20, [], ["Library"], "Libraries +1 science"),
    "Rail Networks":       Technology("Rail Networks", TechBranch.CIVIC, Era.ANCIENT, 30, ["Steam Power"], [], "Trade routes generate gold"),
    "Telegraphy":          Technology("Telegraphy", TechBranch.SCIENTIFIC, Era.ANCIENT, 25, ["Learned Societies"], [], "+1 science to all cities"),
    "Company Militias":    Technology("Company Militias", TechBranch.MILITARY, Era.ANCIENT, 25, [], ["Militia"], "+10% defense in home territory"),
    # ── Age of Steel (Era.CLASSICAL) ──
    "Bessemer Process":    Technology("Bessemer Process", TechBranch.MILITARY, Era.CLASSICAL, 40, ["Deep Mining"], ["Swordsman", "Crossbowman", "Workshop"], "+10% attack vs units"),
    "Reinforced Concrete": Technology("Reinforced Concrete", TechBranch.SCIENTIFIC, Era.CLASSICAL, 35, ["Deep Mining"], ["Wall"], "Unlocks Walls"),
    "Civil Institutions":  Technology("Civil Institutions", TechBranch.CIVIC, Era.CLASSICAL, 50, ["Learned Societies"], ["Temple", "Monk"], "+2 science to Campus"),
    "Marine Engineering":  Technology("Marine Engineering", TechBranch.SCIENTIFIC, Era.CLASSICAL, 45, ["Steam Power"], ["Trireme", "Lighthouse"], "+1 movement to naval"),
    "Cavalry Doctrine":    Technology("Cavalry Doctrine", TechBranch.MILITARY, Era.CLASSICAL, 55, ["Bessemer Process", "Stockyards"], ["Knight", "Stable"], "Unlocks Knight unit"),
    "Commodity Exchanges": Technology("Commodity Exchanges", TechBranch.CIVIC, Era.CLASSICAL, 35, ["Rail Networks"], ["Market", "Trader"], "Trade routes generate gold"),
    "Machine Tools":       Technology("Machine Tools", TechBranch.SCIENTIFIC, Era.CLASSICAL, 60, ["Steam Power", "Deep Mining"], [], "+10% production in all cities"),
    "Refrigeration":       Technology("Refrigeration", TechBranch.SCIENTIFIC, Era.CLASSICAL, 45, ["Canning"], [], "+1 food to all cities"),
    "Corporate Law":       Technology("Corporate Law", TechBranch.CIVIC, Era.CLASSICAL, 50, ["Commodity Exchanges"], [], "Vassal tax bonus +10%"),
    "Munitions Works":     Technology("Munitions Works", TechBranch.MILITARY, Era.CLASSICAL, 55, ["Small Arms"], [], "+10% attack vs cities"),
    # ── Age of Current (Era.MEDIEVAL) ──
    "Electrification":     Technology("Electrification", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 100, ["Machine Tools", "Telegraphy"], [], "+2 production to all cities"),
    "Urban Sanitation":    Technology("Urban Sanitation", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 90, ["Reinforced Concrete"], ["Aqueduct"], "Cities +2 food"),
    "Heavy Artillery":     Technology("Heavy Artillery", TechBranch.MILITARY, Era.MEDIEVAL, 110, ["Munitions Works"], ["Catapult", "Siege Tower"], "Unlocks siege guns"),
    "Mass Schooling":      Technology("Mass Schooling", TechBranch.CIVIC, Era.MEDIEVAL, 100, ["Civil Institutions"], ["University"], "Campus +2 science"),
    "Electric Light":      Technology("Electric Light", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 95, ["Electrification"], [], "+2 happiness in all cities"),
    "Chemical Industry":   Technology("Chemical Industry", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 110, ["Machine Tools"], [], "+1 production from resources"),
    "Labor Unions":        Technology("Labor Unions", TechBranch.CIVIC, Era.MEDIEVAL, 105, ["Corporate Law"], [], "+1 happiness per Workshop"),
    "Steel Navies":        Technology("Steel Navies", TechBranch.MILITARY, Era.MEDIEVAL, 120, ["Marine Engineering", "Bessemer Process"], ["Galley"], "Unlocks armored warships"),
    "Central Banking":     Technology("Central Banking", TechBranch.CIVIC, Era.MEDIEVAL, 115, ["Corporate Law"], ["Bank"], "+25% gold in all cities"),
    "Internal Combustion": Technology("Internal Combustion", TechBranch.SCIENTIFIC, Era.MEDIEVAL, 140, ["Chemical Industry"], [], "+1 movement to land units"),
    # ── Age of Wireless (Era.RENAISSANCE) ──
    "Radio":               Technology("Radio", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 200, ["Electrification", "Telegraphy"], [], "+2 science to all cities"),
    "Mass Production":     Technology("Mass Production", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 220, ["Machine Tools", "Electrification"], ["Factory"], "Unlocks Factory"),
    "Automobiles":         Technology("Automobiles", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 210, ["Internal Combustion"], [], "+1 movement to land units"),
    "Machine Guns":        Technology("Machine Guns", TechBranch.MILITARY, Era.RENAISSANCE, 200, ["Heavy Artillery", "Munitions Works"], [], "Ranged units +2 attack"),
    "Telephone Exchanges": Technology("Telephone Exchanges", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 180, ["Telegraphy", "Electric Light"], [], "+1 gold to all cities"),
    "Modern Medicine":     Technology("Modern Medicine", TechBranch.SCIENTIFIC, Era.RENAISSANCE, 190, ["Chemical Industry", "Urban Sanitation"], [], "Cities +2 food"),
    "Mass Media":          Technology("Mass Media", TechBranch.CIVIC, Era.RENAISSANCE, 185, ["Radio"], ["Newspaper"], "+2 culture to all cities"),
    "Suffrage Movements":  Technology("Suffrage Movements", TechBranch.CIVIC, Era.RENAISSANCE, 195, ["Labor Unions", "Mass Schooling"], [], "+2 happiness in all cities"),
    "Dreadnoughts":        Technology("Dreadnoughts", TechBranch.MILITARY, Era.RENAISSANCE, 240, ["Steel Navies", "Mass Production"], [], "Naval units +4 attack"),
    # ── Age of Flight (Era.INDUSTRIAL) ──
    "Powered Flight":      Technology("Powered Flight", TechBranch.SCIENTIFIC, Era.INDUSTRIAL, 380, ["Automobiles", "Radio"], [], "Reveals distant map"),
    "Assembly Automation": Technology("Assembly Automation", TechBranch.SCIENTIFIC, Era.INDUSTRIAL, 360, ["Mass Production"], [], "+25% production in all cities"),
    "Armored Warfare":     Technology("Armored Warfare", TechBranch.MILITARY, Era.INDUSTRIAL, 400, ["Automobiles", "Machine Guns"], [], "Cavalry units +4 attack"),
    "Aerial Bombardment":  Technology("Aerial Bombardment", TechBranch.MILITARY, Era.INDUSTRIAL, 440, ["Powered Flight"], [], "Siege units +4 attack"),
    "Synthetic Materials": Technology("Synthetic Materials", TechBranch.SCIENTIFIC, Era.INDUSTRIAL, 370, ["Chemical Industry", "Mass Production"], [], "+1 production from resources"),
    "Broadcast Empire":    Technology("Broadcast Empire", TechBranch.CIVIC, Era.INDUSTRIAL, 350, ["Mass Media", "Telephone Exchanges"], [], "+4 culture to all cities"),
    "Welfare State":       Technology("Welfare State", TechBranch.CIVIC, Era.INDUSTRIAL, 340, ["Suffrage Movements", "Modern Medicine"], [], "+4 happiness in all cities"),
    "Rocketry":            Technology("Rocketry", TechBranch.MILITARY, Era.INDUSTRIAL, 460, ["Aerial Bombardment", "Synthetic Materials"], [], "Unlocks rocket artillery"),
    "Radar":               Technology("Radar", TechBranch.SCIENTIFIC, Era.INDUSTRIAL, 420, ["Radio", "Powered Flight"], [], "+2 defense to all units"),
    # ── Age of the Atom (Era.MODERN) ──
    "Atomic Theory":       Technology("Atomic Theory", TechBranch.SCIENTIFIC, Era.MODERN, 600, ["Synthetic Materials", "Radar"], [], "+4 science to all cities"),
    "Nuclear Fission":     Technology("Nuclear Fission", TechBranch.SCIENTIFIC, Era.MODERN, 750, ["Atomic Theory"], [], "Unlocks the atomic age"),
    "Computing Machines":  Technology("Computing Machines", TechBranch.SCIENTIFIC, Era.MODERN, 680, ["Radar", "Assembly Automation"], [], "+25% science in all cities"),
    "Jet Propulsion":      Technology("Jet Propulsion", TechBranch.MILITARY, Era.MODERN, 700, ["Rocketry", "Radar"], [], "Air units +4 attack"),
    "Atomic Weapons":      Technology("Atomic Weapons", TechBranch.MILITARY, Era.MODERN, 850, ["Nuclear Fission", "Rocketry"], [], "The ultimate deterrent"),
    "Nuclear Power":       Technology("Nuclear Power", TechBranch.SCIENTIFIC, Era.MODERN, 780, ["Nuclear Fission"], [], "+4 production to all cities"),
    "Global Institutions": Technology("Global Institutions", TechBranch.CIVIC, Era.MODERN, 650, ["Welfare State", "Broadcast Empire"], [], "+4 culture to all cities"),
    "Mutual Deterrence":   Technology("Mutual Deterrence", TechBranch.CIVIC, Era.MODERN, 800, ["Atomic Weapons", "Global Institutions"], [], "Defensive pacts strengthen"),
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
    cities: List = field(default_factory=list)
    characters: List = field(default_factory=list)
    gold: int = 0
    science: int = 0
    culture: int = 0


CIVILIZATIONS = {
    "Rome": Civilization("Rome", "Legion", "Wall", "+10% melee combat strength", "Republic", ["Bessemer Process", "Reinforced Concrete"], "white", 100, 50, 25, {"diplomacy": 10, "martial": 12, "stewardship": 10, "intrigue": 8}, ["Warrior", "Industrious"]),
    "Greece": Civilization("Greece", "Phalanx", "", "+1 science from all tiles", "Republic", ["Civil Institutions", "Canning"], "lightblue", 80, 80, 30, {"diplomacy": 12, "martial": 10, "stewardship": 8, "intrigue": 10}, ["Scholar", "Charismatic"]),
    "Mesopotamia": Civilization("Mesopotamia", "Chariot", "", "+1 food from Plains tiles", "Monarchy", ["Mechanized Farming", "Stockyards"], "#f5deb3", 120, 40, 20, {"diplomacy": 10, "martial": 11, "stewardship": 12, "intrigue": 7}, ["Industrious", "Diplomat"]),
    "Egypt": Civilization("Egypt", "", "Pyramid", "Wonders cost 20% less", "Theocracy", ["Learned Societies", "Reinforced Concrete"], "#ffd700", 90, 60, 40, {"diplomacy": 11, "martial": 10, "stewardship": 9, "intrigue": 10}, ["Charismatic", "Magnanimous"]),
    "Persia": Civilization("Persia", "", "Satrap", "+1 gold from every resource", "Monarchy", ["Commodity Exchanges", "Corporate Law"], "#800080", 110, 50, 30, {"diplomacy": 12, "martial": 9, "stewardship": 11, "intrigue": 8}, ["Diplomat", "Cunning"]),
    "China": Civilization("China", "", "Gunpowder", "+1 science from every tile", "Republic", ["Mass Schooling", "Mass Media"], "red", 85, 85, 35, {"diplomacy": 10, "martial": 9, "stewardship": 11, "intrigue": 10}, ["Scholar", "Just"]),
    "Mongol": Civilization("Mongol", "", "", "+2 movement for cavalry units", "Custom", ["Stockyards", "Cavalry Doctrine"], "#a52a2a", 70, 30, 15, {"diplomacy": 8, "martial": 14, "stewardship": 7, "intrigue": 11}, ["Warrior", "Brave"]),
    "Viking": Civilization("Viking", "", "Longhouse", "Coastal tiles provide +1 production", "Custom", ["Steel Navies", "Learned Societies"], "#c0c0c0", 95, 45, 20, {"diplomacy": 9, "martial": 13, "stewardship": 8, "intrigue": 10}, ["Warrior", "Opportunistic"]),
    "India": Civilization("India", "", "", "+1 faith from all tiles", "Theocracy", ["Civil Institutions", "Learned Societies"], "#ff9933", 100, 60, 50, {"diplomacy": 12, "martial": 8, "stewardship": 11, "intrigue": 9}, ["Charismatic", "Magnanimous"]),
    "Byzantium": Civilization("Byzantium", "", "Hypodrome", "+1 gold and +1 science from cities", "Oligarchy", ["Marine Engineering", "Commodity Exchanges"], "#000080", 115, 70, 35, {"diplomacy": 11, "martial": 10, "stewardship": 12, "intrigue": 7}, ["Scholar", "Diplomat"]),
    "England": Civilization("England", "", "Longbowman", "Ranged units have +2 attack", "Monarchy", ["Small Arms", "Cavalry Doctrine"], "green", 90, 55, 30, {"diplomacy": 11, "martial": 11, "stewardship": 9, "intrigue": 9}, ["Warrior", "Charismatic"]),
    "Ottoman": Civilization("Ottoman", "", "Janissary", "Gunpowder units cost 20% less", "Theocracy", ["Munitions Works", "Corporate Law"], "teal", 105, 45, 25, {"diplomacy": 10, "martial": 12, "stewardship": 10, "intrigue": 8}, ["Warrior", "Industrious"]),
}

# Great Houses (M52): display names for the fictional-1900 setting. The
# CIVILIZATIONS keys above remain the internal IDs - never rename them.
HOUSE_NAMES = {
    "Rome": "House Aurelian",
    "Greece": "House Argyros",
    "Mesopotamia": "House Alluvane",
    "Egypt": "House Meridian",
    "Persia": "House Sarvane",
    "China": "House Celestine",
    "Mongol": "House Khareth",
    "Viking": "House Norvath",
    "India": "House Suravel",
    "Byzantium": "House Porphyry",
    "England": "House Albric",
    "Ottoman": "House Osmarin",
}


def house_name(civ_key: str) -> str:
    """Display name of a Great House; falls back to the raw key."""
    return HOUSE_NAMES.get(civ_key, civ_key)


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
    "domination": {"type": "control", "value": 0.5, "description": "Control 50% of starting cities"},
    "science":    {"type": "era", "value": Era.MODERN, "description": "Reach Modern Era"},
    "culture":    {"type": "culture", "value": 1000, "description": "Accumulate 1000 culture points"},
    "diplomacy":  {"type": "alliance", "value": 5, "description": "Have 5 allied civilizations"},
    "dynasty":    {"type": "generations", "value": 10, "description": "Survive 10 generations"},
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
