"""
CivKings - External Trade Routes
Handles trade with other civilizations via merchant units.
"""
from typing import Dict, List, Optional, Tuple


class ExternalTradeRoutes:
    """Manages external trade routes between civilizations."""

    # Trade route yields based on cargo type and distance
    CARGO_YIELDS: Dict[str, Dict[str, float]] = {
        "gold": {"base": 5, "per_tile": 0.5},
        "food": {"base": 3, "per_tile": 0.3},
        "science": {"base": 4, "per_tile": 0.4},
        "culture": {"base": 3, "per_tile": 0.3},
        "faith": {"base": 3, "per_tile": 0.3},
    }

    # Trade agreement bonuses
    AGREEMENT_BONUSES: Dict[str, float] = {
        "open_borders": 0.1,
        "trade_agreement": 0.2,
        "customs_union": 0.3,
        "economic_partnership": 0.4,
    }

    def __init__(self):
        self.routes: List[Dict[str, any]] = []
        self.active_agreements: Dict[str, Dict[str, any]] = {}  # civ_name -> agreements
        self.trade_route_count: int = 0
        self._merchant_units: Dict[str, Dict[str, any]] = {}  # unit_name -> route info

    def create_trade_route(self, merchant_unit: str, target_civ: str, cargo: str = "gold") -> bool:
        """Create a trade route between civilizations."""
        if cargo not in self.CARGO_YIELDS:
            return False

        route = {
            "merchant": merchant_unit,
            "target_civ": target_civ,
            "cargo": cargo,
            "yield": self.CARGO_YIELDS[cargo]["base"],
            "status": "active",
            "turns_active": 0,
        }

        # Check for trade agreement bonuses
        if target_civ in self.active_agreements:
            bonuses = self.active_agreements[target_civ]
            for ag_type, multiplier in bonuses.items():
                route["yield"] *= (1 + multiplier)

        self.routes.append(route)
        self.trade_route_count += 1
        return True

    def cancel_trade_route(self, merchant_unit: str) -> bool:
        """Cancel an existing trade route."""
        for i, route in enumerate(self.routes):
            if route["merchant"] == merchant_unit:
                route["status"] = "cancelled"
                self.trade_route_count = max(0, self.trade_route_count - 1)
                return True
        return False

    def establish_trade_agreement(self, civ_a: str, civ_b: str, agreement_type: str = "trade_agreement") -> bool:
        """Establish a trade agreement between two civilizations."""
        if agreement_type not in self.AGREEMENT_BONUSES:
            return False

        if civ_a not in self.active_agreements:
            self.active_agreements[civ_a] = {}
        if civ_b not in self.active_agreements:
            self.active_agreements[civ_b] = {}

        self.active_agreements[civ_a][civ_b] = agreement_type
        self.active_agreements[civ_b][civ_a] = agreement_type
        return True

    def calculate_route_yield(self, route: Dict[str, any]) -> float:
        """Calculate the yield of a trade route."""
        cargo = route["cargo"]
        base_yield = self.CARGO_YIELDS[cargo]["base"]
        
        # Apply agreement bonuses
        bonus = 0.0
        target = route["target_civ"]
        if target in self.active_agreements:
            for ag_type in self.active_agreements[target].values():
                bonus += self.AGREEMENT_BONUSES.get(ag_type, 0)

        yield_ = base_yield * (1 + bonus)
        
        # Apply duration bonus (routes last longer = more stable yields)
        turns = route.get("turns_active", 0)
        if turns > 10:
            yield_ *= 1.1  # 10% bonus for long routes
        if turns > 20:
            yield_ *= 1.05  # Additional 5% bonus

        return yield_

    def process_all_routes(self) -> Dict[str, Dict[str, float]]:
        """Process all active trade routes and return yields per civ."""
        total_yields: Dict[str, Dict[str, float]] = {}

        for route in self.routes:
            if route["status"] != "active":
                continue

            target = route["target_civ"]
            if target not in total_yields:
                total_yields[target] = {}

            cargo = route["cargo"]
            yield_ = self.calculate_route_yield(route)
            
            if cargo not in total_yields[target]:
                total_yields[target][cargo] = 0.0
            
            total_yields[target][cargo] += yield_
            route["turns_active"] += 1

        return total_yields

    def get_route_summary(self) -> Dict[str, any]:
        """Get summary of all trade routes."""
        active_routes = [r for r in self.routes if r["status"] == "active"]
        total_yield = sum(self.calculate_route_yield(r) for r in active_routes)
        
        return {
            "total_routes": len(active_routes),
            "total_yield": round(total_yield, 2),
            "routes_by_cargo": self._count_by_cargo(active_routes),
            "routes_by_civ": self._count_by_civ(active_routes),
        }

    def _count_by_cargo(self, routes: List[Dict[str, any]]) -> Dict[str, int]:
        """Count routes by cargo type."""
        counts: Dict[str, int] = {}
        for route in routes:
            cargo = route["cargo"]
            counts[cargo] = counts.get(cargo, 0) + 1
        return counts

    def _count_by_civ(self, routes: List[Dict[str, any]]) -> Dict[str, int]:
        """Count routes by target civ."""
        counts: Dict[str, int] = {}
        for route in routes:
            civ = route["target_civ"]
            counts[civ] = counts.get(civ, 0) + 1
        return counts

    def add_merchant_unit(self, unit_name: str, unit_data: Dict[str, any]):
        """Register a merchant unit."""
        self._merchant_units[unit_name] = unit_data

    def remove_merchant_unit(self, unit_name: str):
        """Remove a merchant unit."""
        self._merchant_units.pop(unit_name, None)
