"""
CivKings - City Management System
Handles city production, districts, buildings, and population
"""
import math
from typing import List, Dict, Optional, Any
from game_data import (
    BUILDINGS, DISTRICTS, BuildingType, DistrictType,
    ClimateZone, CLIMATE_MODIFIERS, COASTLINE_BONUSES,
    TerrainType, LandmarkType, LANDMARKS,
)

# Map adjacency_bonus keys to TerrainType enum values
TERRAIN_KEY_MAP: Dict[str, TerrainType] = {
    "Mountain": TerrainType.MOUNTAIN,
    "Hills": TerrainType.HILLS,
    "Coast": TerrainType.WATER_COAST,
    "Forest": TerrainType.FOREST,
    "Ocean": TerrainType.OCEAN,
    "Plains": TerrainType.PLAINS,
    "Grassland": TerrainType.GRASSLAND,
    "Desert": TerrainType.DESERT,
    "Tundra": TerrainType.TUNDRA,
}

# Hex neighbor offsets in axial coordinates (q, r)
HEX_OFFSETS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1),
]


class City:
    """Represents a city on the map"""
    
    def __init__(self, name: str, owner: str, position: tuple, population: int = 1, gold: int = 0, climate_zone: ClimateZone = ClimateZone.TEMPERATE, is_coastal: bool = False):
        self.name = name
        self.owner = owner
        self.owner_id = owner
        self.position = position
        self.population = population
        self.gold = gold
        self.production = 0
        self.max_production = 100
        self.production_queue: List[str] = []
        self.current_production: Optional[str] = None
        self.districts: Dict[str, DistrictType] = {}
        self.district_positions: Dict[str, tuple] = {}
        self.buildings: Dict[str, BuildingType] = {}
        self.happiness = 0
        self.science = 0
        self.food = 0
        self.food_reserved = 0
        self.faith = 0
        self.climate_zone = climate_zone
        self.is_coastal = is_coastal
        self._adjacency_scores: Dict[str, Dict[str, float]] = {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "owner": self.owner,
            "position": self.position,
            "population": self.population,
            "gold": self.gold,
            "production": self.production,
            "current_production": self.current_production,
            "production_queue": self.production_queue,
            "districts": list(self.districts.keys()),
            "buildings": list(self.buildings.keys()),
            "happiness": self.happiness,
            "science": self.science,
        }

    def add_district(self, district_type: DistrictType, position: Optional[tuple] = None):
        """Add a district to the city, optionally at a specific tile position."""
        self.districts[district_type.name] = district_type
        if position is not None:
            self.district_positions[district_type.name] = position

    def add_building(self, building_type: BuildingType):
        """Add a building to the city"""
        self.buildings[building_type.name] = building_type

    def calculate_adjacency(self, tiles: Dict[tuple, Any]) -> Dict[str, Dict[str, float]]:
        """Calculate adjacency bonuses for all districts in this city.
        
        Scans adjacent tiles and buildings/districts within the city.
        Returns dict: {district_name: {bonus_type: count}}
        """
        scores: Dict[str, Dict[str, float]] = {}

        for district_name, district in self.districts.items():
            bonus_map: Dict[str, float] = {}
            adj_bonus: Dict[str, float] = district.adjacency_bonus
            if not adj_bonus:
                scores[district_name] = bonus_map
                continue

            # Get the tiles adjacent to this district's position
            # If no specific position, use city center
            tile_to_check = self.district_positions.get(district_name, self.position)
            if tile_to_check is None:
                scores[district_name] = bonus_map
                continue

            adj_tiles = self._get_hex_neighbors(tile_to_check, tiles)

            for tile in adj_tiles:
                if tile is None:
                    continue

                # Check terrain-based bonuses
                for key, terrain in TERRAIN_KEY_MAP.items():
                    if key in adj_bonus and tile.terrain == terrain:
                        bonus_map[key] = bonus_map.get(key, 0) + 1

                # Check river-based bonuses
                if "River" in adj_bonus and tile.has_river:
                    bonus_map["River"] = bonus_map.get("River", 0) + 1

                # Check landmark-based bonuses
                if tile.landmark in adj_bonus:
                    bonus_map[str(tile.landmark)] = bonus_map.get(str(tile.landmark), 0) + 1

            # Check building-based bonuses (e.g., Market bonus for Commercial Hub)
            for building_name, bonus_val in adj_bonus.items():
                if building_name in BUILDINGS and building_name not in TERRAIN_KEY_MAP and building_name not in ("River",):
                    if building_name in self.buildings:
                        bonus_map[building_name] = bonus_map.get(building_name, 0) + 1

            # Check district-to-district bonuses (e.g., Campus next to another Campus)
            for district_name_other, bonus_val in adj_bonus.items():
                if district_name_other in DISTRICTS and district_name_other != district_name:
                    # Check if the other district is adjacent by position
                    other_pos = self.district_positions.get(district_name_other)
                    if other_pos is not None:
                        my_pos = self.district_positions.get(district_name, self.position)
                        if my_pos is not None:
                            # Check if positions are adjacent
                            if self._are_adjacent(my_pos, other_pos):
                                bonus_map[district_name_other] = bonus_map.get(district_name_other, 0) + 1

            scores[district_name] = bonus_map

        self._adjacency_scores = scores
        return scores

    def _are_adjacent(self, pos1: tuple, pos2: tuple) -> bool:
        """Check if two hex positions are adjacent."""
        q1, r1 = pos1
        q2, r2 = pos2
        dq, dr = q2 - q1, r2 - r1
        for dq_off, dr_off in HEX_OFFSETS:
            if dq == dq_off and dr == dr_off:
                return True
        return False

    def _get_hex_neighbors(self, pos: tuple, tiles: Dict[tuple, Any]) -> List[Any]:
        """Get the 6 hex neighbors of a position."""
        neighbors = []
        q, r = pos
        for dq, dr in HEX_OFFSETS:
            nq, nr = q + dq, r + dr
            neighbor = tiles.get((nq, nr))
            if neighbor is not None:
                neighbors.append(neighbor)
        return neighbors

    def _get_adjacency_multiplier(self, district_name: str, stat: str) -> float:
        """Compute the total adjacency multiplier for a district's stat yield.
        
        Sums all matching bonus types from the district's adjacency_bonus dict.
        Returns (multiplier, total_bonus_count) where multiplier = 1 + sum(count * bonus_val).
        """
        scores = self._adjacency_scores.get(district_name, {})
        district = self.districts.get(district_name)
        if not district or not district.adjacency_bonus:
            return 1.0

        total = 0.0
        for bonus_key, bonus_val in district.adjacency_bonus.items():
            count = scores.get(bonus_key, 0)
            total += count * bonus_val

        return 1.0 + total

    def calculate_yields(self, tiles: Optional[Dict[tuple, Any]] = None) -> Dict[str, float]:
        """Calculate total yields for the city, including adjacency bonuses."""
        # Compute adjacency if map tiles are available
        if tiles is not None:
            self.calculate_adjacency(tiles)

        yields = {
            "food": 2.0,
            "gold": 1.0,
            "science": 0.0,
            "production": 3.0,
            "culture": 0.0,
        }

        # Add yields from districts with adjacency bonuses
        for district_name, district in self.districts.items():
            # Science bonus (multiplied by adjacency)
            if district.science_bonus > 0:
                multiplier = self._get_adjacency_multiplier(district_name, "science")
                yields["science"] += district.science_bonus * multiplier

            # Gold bonus (multiplied by adjacency)
            if district.gold_bonus > 0:
                multiplier = self._get_adjacency_multiplier(district_name, "gold")
                yields["gold"] += district.gold_bonus * multiplier

            # Faith bonus (maps to culture)
            if district.faith_bonus > 0:
                multiplier = self._get_adjacency_multiplier(district_name, "faith")
                yields["culture"] += district.faith_bonus * multiplier

            # Happiness bonus (additive, not multiplied)
            if district.happiness_bonus > 0:
                self.happiness += district.happiness_bonus

        # Add yields from buildings
        for building_name, building in self.buildings.items():
            # Building yields are additive (no adjacency for buildings currently)
            if building.food > 0:
                yields["food"] += building.food
            if building.gold > 0:
                yields["gold"] += building.gold
            if building.science > 0:
                yields["science"] += building.science
            if building.production > 0:
                yields["production"] += building.production
            if building.faith > 0:
                yields["culture"] += building.faith
            if building.happiness > 0:
                self.happiness += building.happiness

        # Population bonuses
        yields["food"] += self.population * 0.5
        yields["gold"] += self.population * 0.2

        # Happiness affects production
        if self.happiness < 0:
            yields["production"] *= 0.8
        elif self.happiness > 10:
            yields["production"] *= 1.1

        # Apply climate zone modifiers
        mod = CLIMATE_MODIFIERS[self.climate_zone]
        yields["food"] *= mod.food_multiplier
        yields["production"] *= mod.production_multiplier
        yields["gold"] *= mod.gold_multiplier
        yields["science"] *= mod.science_multiplier
        yields["culture"] *= mod.faith_multiplier
        self.happiness += mod.happiness_modifier

        # Apply coastline bonuses
        if self.is_coastal:
            yields["food"] += COASTLINE_BONUSES["fishing_bonus"]
            yields["gold"] += COASTLINE_BONUSES["trade_route_bonus"]
            if "Harbor" in self.districts:
                yields["gold"] += COASTLINE_BONUSES["harbor_bonus"]

        return yields

    def assign_production(self, item: str):
        """Assign an item to production queue"""
        if item not in self.production_queue:
            self.production_queue.append(item)

    def process_production(self, turn_food: float, turn_gold: float, turn_science: float, turn_production: float):
        """Process one turn of city production"""
        self.gold += turn_gold
        self.science += turn_science
        self.production += turn_production

        if self.production_queue:
            item = self.production_queue[0]
            if self.current_production is None:
                self.current_production = item

            if self.production >= 100:
                if item in self.production_queue:
                    self.production_queue.remove(item)
                self.current_production = None
                self.production = 0
                return item

        return None


class CityManager:
    """Manages all cities in the game"""
    
    def __init__(self, cities):
        if isinstance(cities, dict):
            self.cities = list(cities.values())
        else:
            self.cities = cities

    def get_city(self, name: str) -> Optional[City]:
        """Get a city by name"""
        for city in self.cities:
            if city.name == name:
                return city
        return None

    def get_cities_by_owner(self, owner: str) -> List[City]:
        """Get all cities owned by a civilization"""
        return [city for city in self.cities if city.owner == owner]

    def process_all_cities(self, tiles: Optional[Dict[tuple, Any]] = None) -> Dict[str, Dict[str, float]]:
        """Process all cities and return yields"""
        all_yields = {}
        for city in self.cities:
            yields = city.calculate_yields(tiles)
            all_yields[city.name] = yields

            completed = city.process_production(
                yields["food"],
                yields["gold"],
                yields["science"],
                yields["production"],
            )
            if completed:
                print(f"  {city.name} completed: {completed}")

        return all_yields

    def add_city(self, city: City):
        """Add a city to the manager"""
        self.cities.append(city)

    def remove_city(self, city: City):
        """Remove a city from the manager"""
        if city in self.cities:
            self.cities.remove(city)

    def get_total_yields(self, owner: str, tiles: Optional[Dict[tuple, Any]] = None) -> Dict[str, float]:
        """Get total yields for a civilization"""
        total = {"food": 0.0, "gold": 0.0, "science": 0.0, "production": 0.0, "culture": 0.0}

        for city in self.get_cities_by_owner(owner):
            yields = city.calculate_yields(tiles)
            for stat, value in yields.items():
                total[stat] += value

        return total
