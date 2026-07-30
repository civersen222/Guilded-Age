"""
CivKings - Market Simulation
Handles resource scarcity, price fluctuations, and market dynamics.
"""
from typing import Dict, List, Optional, Tuple
import random


class MarketSimulation:
    """Simulates a dynamic market with supply/demand and price fluctuations."""

    # Base prices for core resources
    BASE_PRICES: Dict[str, float] = {
        "Gold": 1.0,
        "Food": 1.0,
        "Science": 1.0,
        "Culture": 1.0,
        "Faith": 1.0,
        # Luxury resources
        "Luxury_Wine": 2.5,
        "Luxury_Oil": 3.0,
        "Luxury_Ivory": 4.0,
        "Luxury_Spices": 3.5,
        "Luxury_Fur": 2.0,
        "Luxury_Pearls": 5.0,
        "Luxury_Silk": 6.0,
        "Luxury_Marble": 3.0,
        "Luxury_Gems": 5.5,
        "Luxury_Exotic_Animals": 7.0,
        "Luxury_Tapestries": 4.5,
        "Luxury_Incense": 3.5,
        "Luxury_Cotton": 2.0,
        "Luxury_Rubber": 3.5,
        "Luxury_Coffee": 3.0,
        "Luxury_Tea": 3.5,
        "Luxury_Chocolate": 4.0,
        "Luxury_Tobacco": 2.5,
        "Luxury_Sugar": 2.0,
        "Luxury_Timber": 1.5,
        "Luxury_Iron": 2.0,
        "Luxury_Copper": 1.5,
        "Luxury_Bronze": 2.5,
        "Luxury_Salt": 1.0,
        "Luxury_Fish": 0.8,
        "Luxury_Wheat": 0.9,
        "Luxury_Meat": 1.2,
        "Luxury_Fruits": 1.0,
        "Luxury_Vegetables": 0.8,
    }

    def __init__(self):
        self.prices: Dict[str, float] = {k: v for k, v in self.BASE_PRICES.items()}
        self.supply: Dict[str, float] = {k: 100.0 for k in self.BASE_PRICES.keys()}
        self.demand: Dict[str, float] = {k: 50.0 for k in self.BASE_PRICES.keys()}
        self.market_events: List[Dict[str, any]] = []
        self.price_history: Dict[str, List[float]] = {k: [v] for k, v in self.BASE_PRICES.items()}
        self.max_history: int = 100

    def update_supply_demand(self, resource: str, supply_delta: float, demand_delta: float):
        """Update supply and demand for a resource."""
        if resource not in self.supply:
            self.supply[resource] = 100.0
        if resource not in self.demand:
            self.demand[resource] = 50.0

        self.supply[resource] = max(0, self.supply[resource] + supply_delta)
        self.demand[resource] = max(0, self.demand[resource] + demand_delta)

    def calculate_price(self, resource: str) -> float:
        """Calculate current price based on supply/demand."""
        base = self.BASE_PRICES.get(resource, 1.0)
        supply = self.supply.get(resource, 100.0)
        demand = self.demand.get(resource, 50.0)

        if supply == 0:
            price = base * 10.0
        else:
            price = base * (demand / supply)

        fluctuation = random.uniform(0.9, 1.1)
        price *= fluctuation

        price = max(0.1, min(100.0, price))
        return price

    def update_all_prices(self):
        """Update all resource prices."""
        for resource in self.BASE_PRICES.keys():
            old_price = self.prices.get(resource, self.BASE_PRICES[resource])
            new_price = self.calculate_price(resource)
            self.prices[resource] = new_price
            self.price_history[resource].append(new_price)
            if len(self.price_history[resource]) > self.max_history:
                self.price_history[resource] = self.price_history[resource][-self.max_history:]

            if abs(new_price - old_price) / old_price > 0.2:
                if new_price > old_price:
                    direction = "UP"
                else:
                    direction = "DOWN"
                change_pct = ((new_price - old_price) / old_price) * 100
                self.market_events.append({
                    "resource": resource,
                    "direction": direction,
                    "change_pct": change_pct,
                    "new_price": new_price,
                    "old_price": old_price,
                })

    def simulate_market_event(self):
        """Simulate a random market event."""
        if not self.BASE_PRICES:
            return
        
        resource = random.choice(list(self.BASE_PRICES.keys()))
        supply_delta = random.uniform(-20, 20)
        demand_delta = random.uniform(-20, 20)
        self.update_supply_demand(resource, supply_delta, demand_delta)
        
        event_type = random.choice(["supply_shock", "demand_surge", "trade_disruption", "abundance"])
        event_desc = {
            "supply_shock": f"Supply shock for {resource}!",
            "demand_surge": f"Demand surge for {resource}!",
            "trade_disruption": f"Trade disruption affects {resource}!",
            "abundance": f"Abundance of {resource} detected!",
        }
        
        self.market_events.append({
            "type": event_type,
            "resource": resource,
            "description": event_desc[event_type],
            "turn": 0,
        })

    def get_price_trend(self, resource: str, periods: int = 5) -> str:
        """Get price trend for a resource."""
        history = self.price_history.get(resource, [])
        if len(history) < periods:
            return "SAME"

        recent = history[-periods:]
        if recent[-1] > recent[0] * 1.1:
            return "UP"
        elif recent[-1] < recent[0] * 0.9:
            return "DOWN"
        return "SAME"
