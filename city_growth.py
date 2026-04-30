"""
CivKings - City Growth & Building System
Handles city growth mechanics, building prerequisites, wonders, and worker improvements.
"""
from typing import List, Dict, Optional, Tuple, Set
from game_data import (
    BuildingType, DistrictType, TerrainType,
    BUILDINGS, DISTRICTS, WONDERS, WorkerImprovementType
)
from enum import Enum


class GrowthState(Enum):
    STAGNANT = "Stagnant"
    GROWING = "Growing"
    STARVING = "Starving"
    OVERCROWDED = "Overcrowded"


class CityGrowthSystem:
    """Manages city population growth mechanics."""
    
    # Food needed for next population level
    POPULATION_FOOD_TABLE = {
        1: 0, 2: 10, 3: 25, 4: 45, 5: 70,
        6: 100, 7: 135, 8: 175, 9: 220, 10: 270,
    }
    
    # Max population based on city features
    POPULATION_CAPS = {
        "base": 20,  # Default max population
        "aqueduct": 5,  # Aqueduct bonus
        "sewage_system": 3,  # Sewer System bonus
        "harbor": 2,  # Harbor bonus for coastal cities
        "coastal": 2,  # Coastal city bonus
    }
    
    @staticmethod
    def get_food_needed_for_next_level(population: int) -> int:
        """Get food needed to reach next population level."""
        if population in CityGrowthSystem.POPULATION_FOOD_TABLE:
            return CityGrowthSystem.POPULATION_FOOD_TABLE[population]
        # Extrapolate for population > 10
        return int(CityGrowthSystem.POPULATION_FOOD_TABLE[10] * (population / 10) ** 1.2)
    
    @staticmethod
    def calculate_max_population(city) -> int:
        """Calculate maximum population for a city based on its features."""
        max_pop = CityGrowthSystem.POPULATION_CAPS["base"]
        
        # Add bonuses from buildings
        for building_name in city.buildings:
            if building_name == "Aqueduct":
                max_pop += CityGrowthSystem.POPULATION_CAPS["aqueduct"]
            elif building_name == "Sewer System":
                max_pop += CityGrowthSystem.POPULATION_CAPS["sewage_system"]
        
        # Add bonuses from districts
        for district_name in city.districts:
            if district_name == "Harbor":
                max_pop += CityGrowthSystem.POPULATION_CAPS["harbor"]
        
        # Add coastal bonus
        if city.is_coastal:
            max_pop += CityGrowthSystem.POPULATION_CAPS["coastal"]
        
        # Add wonder bonuses
        if "Colosseum" in WONDERS:
            # Check if Colosseum is built anywhere
            # This would need to check global wonders
            pass
        
        return max_pop
    
    @staticmethod
    def process_growth(city, food_surplus: float) -> GrowthState:
        """Process city growth and return current growth state."""
        max_pop = CityGrowthSystem.calculate_max_population(city)
        current_pop = city.population
        
        # Check if city is starving
        if food_surplus < -2:
            return GrowthState.STARVING
        
        # Check if city is growing
        if food_surplus > 0 and current_pop < max_pop:
            # Accumulate food
            city.food = food_surplus
            
            # Check if we have enough food to grow
            food_needed = CityGrowthSystem.get_food_needed_for_next_level(current_pop)
            
            if city.food >= food_needed:
                city.population += 1
                city.food = 0  # Reset food after growth
                return GrowthState.GROWING
        
        # Check if city is stagnant (no growth, no starvation)
        if food_surplus >= 0 and current_pop < max_pop:
            return GrowthState.STAGNANT
        
        # Check if city is overcrowded (at max population)
        if current_pop >= max_pop:
            return GrowthState.OVERCROWDED
        
        return GrowthState.STAGNANT


class BuildingPrerequisiteSystem:
    """Manages building prerequisite chains."""
    
    # Building prerequisites: {building: [required_buildings]}
    PREREQUISITES = {
        "Granary": [],  # No prerequisites
        "Food Market": ["Granary"],
        "Bank": ["Food Market"],
        "Stock Exchange": ["Bank"],
        "Aqueduct": [],
        "Sewer System": ["Aqueduct"],
        "Harbor": [],
        "Lighthouse": ["Harbor"],
        "Palace": [],  # Special building
        "Temple": ["Palace"],
        "University": ["Palace"],
        "Library": ["Palace"],
        "Library": ["Palace"],
        "Barracks": ["Palace"],
        "Military Academy": ["Barracks"],
    }
    
    @staticmethod
    def can_build(building_name: str, city) -> Tuple[bool, List[str]]:
        """Check if a building can be built and return any missing prerequisites."""
        if building_name not in BUILDINGS:
            return False, [f"Unknown building: {building_name}"]
        
        prerequisites = BuildingPrerequisiteSystem.PREREQUISITES.get(building_name, [])
        missing = []
        
        for prereq in prerequisites:
            if prereq not in city.buildings:
                missing.append(prereq)
        
        return len(missing) == 0, missing


class WonderSystem:
    """Manages world wonders (one-time global effects)."""
    
    # Wonders that have been built
    built_wonders: Set[str] = set()
    
    # Wonders that are currently under construction
    construction_queue: Dict[str, int] = {}  # wonder_name -> turns remaining
    
    @staticmethod
    def can_build_wonder(wonder_name: str, city) -> bool:
        """Check if a wonder can be built in a city."""
        if wonder_name in WonderSystem.built_wonders:
            return False  # Already built
        
        if wonder_name not in WONDERS:
            return False  # Unknown wonder
        
        # Check if city has required district
        wonder = WONDERS[wonder_name]
        required_district = wonder.get("required_district")
        if required_district and required_district not in city.districts:
            return False
        
        return True
    
    @staticmethod
    def start_construction(wonder_name: str, city, turns_required: int) -> bool:
        """Start construction of a wonder."""
        if not WonderSystem.can_build_wonder(wonder_name, city):
            return False
        
        WonderSystem.construction_queue[wonder_name] = turns_required
        return True
    
    @staticmethod
    def process_construction(city, turn_production: float) -> Optional[str]:
        """Process wonder construction and return completed wonder if any."""
        completed_wonders = []
        
        for wonder_name, turns_remaining in list(WonderSystem.construction_queue.items()):
            turns_remaining -= turn_production / 100  # Convert to turns
            WonderSystem.construction_queue[wonder_name] = turns_remaining
            
            if turns_remaining <= 0:
                completed_wonders.append(wonder_name)
                WonderSystem.built_wonders.add(wonder_name)
                del WonderSystem.construction_queue[wonder_name]
                
                # Apply wonder effects
                if wonder_name in WONDERS:
                    effects = WONDERS[wonder_name].get("effects", {})
                    for effect_type, value in effects.items():
                        # Apply effects to the game world
                        pass
        
        return completed_wonders[0] if completed_wonders else None


class WorkerImprovementSystem:
    """Manages worker improvements on tiles."""
    
    # Improvement yields
    IMPROVEMENT_YIELDS = {
        "Farm": {"food": 2, "gold": 0},
        "Mine": {"food": 0, "production": 2},
        "Pasture": {"food": 1, "gold": 1},
        "Quarry": {"food": 0, "production": 3},
        "Plantation": {"food": 1, "gold": 2},
    }
    
    # Terrain compatibility for improvements
    TERRAIN_COMPATIBILITY = {
        "Farm": [TerrainType.PLAINS, TerrainType.GRASSLAND],
        "Mine": [TerrainType.HILLS, TerrainType.MOUNTAIN],
        "Pasture": [TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.HILLS],
        "Quarry": [TerrainType.HILLS, TerrainType.MOUNTAIN],
        "Plantation": [TerrainType.JUNGLE, TerrainType.FOREST],
    }
    
    @staticmethod
    def can_improve(tile, improvement_type: str) -> bool:
        """Check if a tile can be improved."""
        terrain = tile.terrain
        compatible_terrains = WorkerImprovementSystem.TERRAIN_COMPATIBILITY.get(improvement_type, [])
        return terrain in compatible_terrains
    
    @staticmethod
    def apply_improvement(tile, improvement_type: str) -> Dict[str, float]:
        """Apply improvement to a tile and return new yields."""
        tile.improvement = improvement_type
        yields = WorkerImprovementSystem.IMPROVEMENT_YIELDS.get(improvement_type, {})
        return yields


class CityGrowthManager:
    """Manages all city growth and building systems."""
    
    def __init__(self):
        self.growth_system = CityGrowthSystem()
        self.prerequisite_system = BuildingPrerequisiteSystem()
        self.wonder_system = WonderSystem()
        self.worker_system = WorkerImprovementSystem()
    
    def process_city_growth(self, city, food_surplus: float) -> GrowthState:
        """Process city growth and return current state."""
        return self.growth_system.process_growth(city, food_surplus)
    
    def check_building_prerequisites(self, city, building_name: str) -> Tuple[bool, List[str]]:
        """Check if a building can be built."""
        return self.prerequisite_system.can_build(building_name, city)
    
    def get_available_buildings(self, city) -> List[str]:
        """Get list of buildings that can be built in a city."""
        available = []
        for building_name in BUILDINGS:
            can_build, _ = self.check_building_prerequisites(city, building_name)
            if can_build:
                available.append(building_name)
        return available
    
    def process_all_cities_growth(self, cities, tiles: Dict[tuple, any]) -> Dict[str, GrowthState]:
        """Process growth for all cities."""
        states = {}
        for city in cities:
            yields = city.calculate_yields(tiles)
            food_surplus = yields["food"] - (city.population * 0.5)  # Food consumed by population
            state = self.process_city_growth(city, food_surplus)
            states[city.name] = state
        return states
