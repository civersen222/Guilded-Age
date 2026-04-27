"""
CivKings - City Management System
Handles city production, districts, buildings, and population
"""
from typing import List, Dict, Optional
from game_data import BUILDINGS, DISTRICTS, BuildingType, DistrictType


class City:
    """Represents a city on the map"""
    
    def __init__(self, name: str, owner: str, position: tuple, population: int = 1, gold: int = 0):
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
        self.buildings: Dict[str, BuildingType] = {}
        self.happiness = 0
        self.science = 0
        self.food = 0
        self.food_reserved = 0
        self.faith = 0
    
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
            "science": self.science
        }
    
    def add_district(self, district_type: DistrictType):
        """Add a district to the city"""
        self.districts[district_type.name] = district_type
    
    def add_building(self, building_type: BuildingType):
        """Add a building to the city"""
        self.buildings[building_type.name] = building_type
    
    def calculate_yields(self) -> Dict[str, float]:
        """Calculate total yields for the city"""
        yields = {
            "food": 2,  # Base food from city center
            "gold": 1,
            "science": 0,
            "production": 3,
            "culture": 0
        }
        
        # Add yields from districts
        for district in self.districts.values():
            for stat, value in district.base_yields.items():
                yields[stat] = yields.get(stat, 0) + value
        
        # Add yields from buildings
        for building in self.buildings.values():
            for stat, value in building.base_yields.items():
                yields[stat] = yields.get(stat, 0) + value
        
        # Add population bonuses
        yields["food"] += self.population * 0.5
        yields["gold"] += self.population * 0.2
        
        # Happiness affects production
        if self.happiness < 0:
            yields["production"] *= 0.8
        elif self.happiness > 10:
            yields["production"] *= 1.1
        
        return yields
    
    def assign_production(self, item: str):
        """Assign an item to production queue"""
        if item not in self.production_queue:
            self.production_queue.append(item)
    
    def process_production(self, turn_food: float, turn_gold: float, turn_science: float, turn_production: float):
        """Process one turn of city production"""
        # Add base yields
        self.gold += turn_gold
        self.science += turn_science
        self.production += turn_production
        
        # Process production queue
        if self.production_queue:
            item = self.production_queue[0]
            if self.current_production is None:
                self.current_production = item
            
            # Check if production is complete
            if self.production >= 100:  # Simplified completion threshold
                if item in self.production_queue:
                    self.production_queue.remove(item)
                self.current_production = None
                self.production = 0
                return item  # Return completed item
        
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
    
    def process_all_cities(self) -> Dict[str, Dict[str, float]]:
        """Process all cities and return yields"""
        all_yields = {}
        for city in self.cities:
            yields = city.calculate_yields()
            all_yields[city.name] = yields
            
            # Process production
            completed = city.process_production(
                yields["food"],
                yields["gold"],
                yields["science"],
                yields["production"]
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
    
    def get_total_yields(self, owner: str) -> Dict[str, float]:
        """Get total yields for a civilization"""
        total = {
            "food": 0,
            "gold": 0,
            "science": 0,
            "production": 0,
            "culture": 0
        }
        
        for city in self.get_cities_by_owner(owner):
            yields = city.calculate_yields()
            for stat, value in yields.items():
                total[stat] += value
        
        return total
