"""
CivKings - Economy Management System
Handles gold, science, resources, and trade
"""
from typing import Dict, List, Optional, Tuple


class EconomyManager:
    """Manages the economy (gold, science, resources)"""
    
    def __init__(self):
        self.gold = 0
        self.science = 0
        self.food = 0
        self.culture = 0
        self.faith = 0
        self.trade_routes: List[Dict[str, any]] = []
        self.resources: Dict[str, int] = {}
    
    def add_gold(self, amount: int, source: str = "economy"):
        """Add gold to the economy"""
        self.gold += amount
    
    def add_science(self, amount: int, source: str = "economy"):
        """Add science to the economy"""
        self.science += amount
    
    def add_food(self, amount: int, source: str = "economy"):
        """Add food to the economy"""
        self.food += amount
    
    def add_culture(self, amount: int, source: str = "economy"):
        """Add culture to the economy"""
        self.culture += amount
    
    def add_faith(self, amount: int, source: str = "economy"):
        """Add faith to the economy"""
        self.faith += amount
    
    def spend_gold(self, amount: int) -> bool:
        """Spend gold, returns True if successful"""
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False
    
    def create_trade_route(self, source: str, destination: str, cargo: str = "gold") -> bool:
        """Create a trade route between two locations"""
        route = {
            "source": source,
            "destination": destination,
            "cargo": cargo,
            "yield": 0
        }
        
        # Calculate trade yield
        if cargo == "gold":
            route["yield"] = 5
            self.add_gold(5, "trade_route")
        elif cargo == "food":
            route["yield"] = 3
            self.add_food(3, "trade_route")
        elif cargo == "science":
            route["yield"] = 4
            self.add_science(4, "trade_route")
        
        self.trade_routes.append(route)
        return True
    
    def process_trade_routes(self) -> int:
        """Process all active trade routes"""
        total_yield = 0
        for route in self.trade_routes:
            total_yield += route["yield"]
        return total_yield
    
    def get_resource(self, resource_name: str) -> int:
        """Get amount of a resource"""
        return self.resources.get(resource_name, 0)
    
    def add_resource(self, resource_name: str, amount: int):
        """Add a resource"""
        self.resources[resource_name] = self.resources.get(resource_name, 0) + amount
    
    def process_income(self) -> Dict[str, int]:
        """Process all income sources"""
        income = {
            "gold": self.gold,
            "science": self.science,
            "food": self.food,
            "culture": self.culture,
            "faith": self.faith
        }
        return income
    
    def get_totals(self) -> Dict[str, int]:
        """Get all economy totals"""
        return {
            "gold": self.gold,
            "science": self.science,
            "food": self.food,
            "culture": self.culture,
            "faith": self.faith
        }
