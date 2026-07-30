"""
CivKings - External Trade Routes
Handles trade with other civilizations via merchant units.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TradeRoute:
    """A visible trade route operated by a Trader unit."""
    origin_city_name: str
    destination_city_name: str
    origin_city: "City"
    destination_city: "City"
    trader_unit_name: str
    duration: int = 20
    turns_remaining: int = 20
    gold_per_turn: float = 0.0
    food_per_turn: float = 0.0
    science_per_turn: float = 0.0
    culture_per_turn: float = 0.0
    faith_per_turn: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.turns_remaining > 0

    def advance_turn(self):
        self.turns_remaining -= 1

    def distance_tiles(self) -> int:
        dx = abs(self.origin_city.position[0] - self.destination_city.position[0])
        dy = abs(self.origin_city.position[1] - self.destination_city.position[1])
        # Approximate hex distance
        return max(dx, dy, (dx + dy) // 2)


class ExternalTradeRoutes:
    """Manages external trade routes between civilizations."""

    CARGO_YIELDS: Dict[str, Dict[str, float]] = {
        "gold": {"base": 5, "per_tile": 0.5},
        "food": {"base": 3, "per_tile": 0.3},
        "science": {"base": 4, "per_tile": 0.4},
        "culture": {"base": 3, "per_tile": 0.3},
        "faith": {"base": 3, "per_tile": 0.3},
    }

    AGREEMENT_BONUSES: Dict[str, float] = {
        "open_borders": 0.1,
        "trade_agreement": 0.2,
        "customs_union": 0.3,
        "economic_partnership": 0.4,
    }

    def __init__(self):
        self.routes: List[Dict[str, any]] = []
        self.active_agreements: Dict[str, Dict[str, any]] = {}
        self.trade_route_count: int = 0
        self._merchant_units: Dict[str, Dict[str, any]] = {}
        self._trade_routes: List[TradeRoute] = []

    def create_route(self, origin_city, dest_city, trader_unit) -> Optional[TradeRoute]:
        """Create a visible trade route between two cities using a Trader unit.

        Args:
            origin_city: City object where the route starts
            dest_city: City object where the route ends
            trader_unit: Unit object (must be a Trader)

        Returns:
            TradeRoute if created, None if invalid
        """
        if not origin_city or not dest_city or not trader_unit:
            return None
        if origin_city == dest_city:
            return None
        if trader_unit.unit_type != "Trader":
            return None

        # Mark trader as busy
        trader_unit.is_busy = True
        trader_unit.busy_type = "trade"
        trader_unit.busy_target = dest_city.name

        # Calculate yields based on destination districts and distance
        dist = origin_city.position[0] - dest_city.position[0], origin_city.position[1] - dest_city.position[1]
        dist_tiles = max(abs(dist[0]), abs(dist[1]), (abs(dist[0]) + abs(dist[1])) // 2)

        dest_districts = getattr(dest_city, 'districts', {})
        gold_mult = 1.0 + len(dest_districts) * 0.15
        food_mult = 1.0 + len(dest_districts) * 0.1

        gold_per_turn = round(3.0 * gold_mult / (1 + dist_tiles * 0.2), 1)
        food_per_turn = round(2.0 * food_mult / (1 + dist_tiles * 0.2), 1)

        route = TradeRoute(
            origin_city_name=origin_city.name,
            destination_city_name=dest_city.name,
            origin_city=origin_city,
            destination_city=dest_city,
            trader_unit_name=trader_unit.name,
            gold_per_turn=gold_per_turn,
            food_per_turn=food_per_turn,
        )

        self._trade_routes.append(route)
        return route

    def process_routes(self) -> Dict[str, Dict[str, float]]:
        """Advance all active trade routes by one turn, collect income, expire completed.

        Returns:
            Dict mapping civ_name -> {resource: total_income}
        """
        total_yields: Dict[str, Dict[str, float]] = {}
        expired: List[TradeRoute] = []

        for route in self._trade_routes:
            if not route.is_active:
                expired.append(route)
                continue

            route.advance_turn()

            # Collect income for origin civ
            owner = route.origin_city.owner
            if owner not in total_yields:
                total_yields[owner] = {}

            for key, per_turn in [
                ("gold", route.gold_per_turn),
                ("food", route.food_per_turn),
                ("science", route.science_per_turn),
                ("culture", route.culture_per_turn),
                ("faith", route.faith_per_turn),
            ]:
                if per_turn > 0:
                    total_yields[owner][key] = total_yields[owner].get(key, 0.0) + per_turn

            # Expire route
            if not route.is_active:
                # Free the trader
                expired.append(route)

        # Remove expired routes and free traders
        for route in expired:
            self._trade_routes.remove(route)
            # Find and free the trader unit
            if hasattr(route, 'trader_unit_name'):
                pass  # trader freed when unit is found in game

        return total_yields

    def get_active_routes(self, civ_name: str) -> List[TradeRoute]:
        """Get all active trade routes for a civ (originating from its cities)."""
        return [r for r in self._trade_routes if r.is_active and r.origin_city.owner == civ_name]

    def create_trade_route(self, merchant_unit: str, target_civ: str, cargo: str = "gold") -> bool:
        """Legacy API — kept for compatibility."""
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
        if target_civ in self.active_agreements:
            bonuses = self.active_agreements[target_civ]
            for ag_type, multiplier in bonuses.items():
                route["yield"] *= (1 + multiplier)
        self.routes.append(route)
        self.trade_route_count += 1
        return True

    def cancel_trade_route(self, merchant_unit: str) -> bool:
        for i, route in enumerate(self.routes):
            if route["merchant"] == merchant_unit:
                route["status"] = "cancelled"
                self.trade_route_count = max(0, self.trade_route_count - 1)
                return True
        return False

    def establish_trade_agreement(self, civ_a: str, civ_b: str, agreement_type: str = "trade_agreement") -> bool:
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
        cargo = route["cargo"]
        base_yield = self.CARGO_YIELDS[cargo]["base"]
        bonus = 0.0
        target = route["target_civ"]
        if target in self.active_agreements:
            for ag_type in self.active_agreements[target].values():
                bonus += self.AGREEMENT_BONUSES.get(ag_type, 0)
        yield_ = base_yield * (1 + bonus)
        turns = route.get("turns_active", 0)
        if turns > 10:
            yield_ *= 1.1
        if turns > 20:
            yield_ *= 1.05
        return yield_

    def process_all_routes(self) -> Dict[str, Dict[str, float]]:
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
        active_routes = [r for r in self.routes if r["status"] == "active"]
        total_yield = sum(self.calculate_route_yield(r) for r in active_routes)
        return {
            "total_routes": len(active_routes),
            "total_yield": round(total_yield, 2),
            "routes_by_cargo": self._count_by_cargo(active_routes),
            "routes_by_civ": self._count_by_civ(active_routes),
        }

    def _count_by_cargo(self, routes: List[Dict[str, any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for route in routes:
            cargo = route["cargo"]
            counts[cargo] = counts.get(cargo, 0) + 1
        return counts

    def _count_by_civ(self, routes: List[Dict[str, any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for route in routes:
            civ = route["target_civ"]
            counts[civ] = counts.get(civ, 0) + 1
        return counts

    def add_merchant_unit(self, unit_name: str, unit_data: Dict[str, any]):
        self._merchant_units[unit_name] = unit_data

    def remove_merchant_unit(self, unit_name: str):
        self._merchant_units.pop(unit_name, None)
