"""Stage 4 L1 — Market core: four-commodity production chain with emergent prices.

Coal → Steel → Freight (+ Farm), prices cleared each turn from real supply
and demand. Deterministic: no game.rng in clearing.
"""

from typing import Dict

COMMODITIES = ["coal", "steel", "freight", "farm"]

PRICE_MIN = 0.1
PRICE_MAX = 10.0
DAMPING = 0.2
TARGET = 1.0

# Production chain: what each enterprise kind produces and consumes
PRODUCES = {
    "colliery": "coal",
    "ironworks": "steel",
    "mill": "freight",
    "rail_co": "freight",
    "estate": "farm",
    "bank": None,
}

CONSUMES = {
    "ironworks": "coal",
    "mill": "steel",
    "rail_co": "steel",
}

# Input cost per unit of consumed commodity
INPUT_COST_PER_UNIT = 0.3

# Base demand from population (farm demand scales with total pop)
BASE_FARM_DEMAND_PER_POP = 0.01

# Construction demand: enterprises under construction need steel
CONSTRUCTION_STEEL_DEMAND = 5.0

# Strike reduces supply by this factor
STRIKE_SUPPLY_REDUCTION = 0.5


def clear_price(prev: float, supply: float, demand: float,
                damping: float = DAMPING,
                price_min: float = PRICE_MIN,
                price_max: float = PRICE_MAX) -> float:
    """Clear a price: damp from prev toward demand/supply target, clamp to bounds."""
    if supply > 0:
        target = demand / supply
    else:
        # No supply → push price up
        target = price_max
    price = prev + (target - prev) * damping
    return max(price_min, min(price_max, price))


def supply_by_commodity(game) -> Dict[str, float]:
    """Total supply of each commodity from all operating enterprises."""
    supply: Dict[str, float] = {c: 0.0 for c in COMMODITIES}
    provinces = game.atlas.provinces

    for ent in game.enterprises:
        if ent.under_construction > 0:
            continue
        province = provinces.get(ent.province)
        if province is None:
            continue

        commodity = PRODUCES.get(ent.kind)
        if commodity is None:
            continue

        # Supply = tier * richness (same as capacity_out formula)
        richness = _richness(ent, province)
        if richness <= 0:
            continue

        raw_supply = ent.tier * richness

        # Check for strike on this province — reduces supply
        mv = getattr(province, "movement", None)
        if mv is not None and getattr(mv, "state", None) == "striking":
            raw_supply *= STRIKE_SUPPLY_REDUCTION

        supply[commodity] += raw_supply

    return supply


def demand_by_commodity(game) -> Dict[str, float]:
    """Total demand for each commodity from all enterprises."""
    demand: Dict[str, float] = {c: 0.0 for c in COMMODITIES}
    provinces = game.atlas.provinces

    # Base demand from consumption relationships
    for ent in game.enterprises:
        if ent.under_construction > 0:
            continue
        commodity = CONSUMES.get(ent.kind)
        if commodity is not None:
            # Demand scales with tier (bigger operations need more input)
            demand[commodity] += ent.tier * 1.0

    # Construction demand for steel
    for ent in game.enterprises:
        if ent.under_construction > 0:
            demand["steel"] += CONSTRUCTION_STEEL_DEMAND

    # Farm demand from population
    total_pop = 0
    for pid, prov in provinces.items():
        total_pop += getattr(prov, 'population', 0)
    demand["farm"] += total_pop * BASE_FARM_DEMAND_PER_POP

    return demand


def _richness(ent, province) -> float:
    """Get the richness of the needed endowment for this enterprise."""
    needed_map = {
        "colliery": "coalfield",
        "ironworks": "iron",
        "mill": "timber",
        "rail_co": "harbor",
        "estate": "farmland",
    }
    needed = needed_map.get(ent.kind)
    if needed is None:
        return 1.0
    return float(province.endowments.get(needed, 0))


class Market:
    """Emergent-price market for the four-commodity production chain."""

    def __init__(self):
        self.prices: Dict[str, float] = {c: TARGET for c in COMMODITIES}

    def price(self, commodity: str) -> float:
        """Current price of a commodity."""
        return self.prices.get(commodity, TARGET)

    def clear(self, game) -> None:
        """Clear all commodity markets for this turn."""
        supply = supply_by_commodity(game)
        demand = demand_by_commodity(game)

        for c in COMMODITIES:
            prev = self.prices[c]
            s = supply[c]
            d = demand[c]
            self.prices[c] = clear_price(prev=prev, supply=s, demand=d)

    def confidence(self) -> float:
        """Average price across all commodities — market health indicator."""
        return sum(self.prices[c] for c in COMMODITIES) / len(COMMODITIES)

    def output_mod(self, ent) -> float:
        """Multiplier for enterprise output based on commodity prices.

        Producers price off their output commodity. Banks price off confidence.
        """
        commodity = PRODUCES.get(ent.kind)
        if commodity is not None:
            return self.prices.get(commodity, TARGET)
        # Bank and others: use market confidence
        return self.confidence()

    def input_cost(self, ent) -> float:
        """Input cost deducted from consumers' take.

        Pure producers (colliery, estate) pay nothing.
        Consumers (ironworks, mill, rail_co) pay based on input price.
        """
        commodity = CONSUMES.get(ent.kind)
        if commodity is None:
            return 0.0
        return INPUT_COST_PER_UNIT * self.prices.get(commodity, TARGET)

    def value(self, ent, game) -> float:
        """Enterprise value: capacity output × commodity price."""
        provinces = game.atlas.provinces
        province = provinces.get(ent.province)
        if province is None or ent.under_construction > 0:
            return 0.0

        commodity = PRODUCES.get(ent.kind)
        if commodity is None:
            return 0.0

        richness = _richness(ent, province)
        if richness <= 0:
            return 0.0

        capacity = ent.tier * richness
        return capacity * self.prices.get(commodity, TARGET)


def tech_mod_for(province) -> float:
    """Tech modifier based on province development level.

    Activated development boosts output. Maps development to a multiplier.
    """
    dev = getattr(province, 'development', 0)
    if dev <= 0:
        return 1.0
    return 1.0 + dev * 0.1
