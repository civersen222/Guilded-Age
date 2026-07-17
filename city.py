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
    UNIT_TYPES, UnitType,
    WONDERS, BUILT_WONDERS, WonderType,
    TECHNOLOGIES, Era,
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
        self.production_capacity = 100
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
        # Tile ownership & border growth (deep-systems spec 1.3/1.7)
        self.owned_tiles: set = set()      # (x, y) positions this city owns and may work
        self.initialize_borders()
        self.culture_basket: float = 0.0   # culture stored toward the next tile claim
        self.tiles_claimed: int = 0        # tiles claimed beyond the initial radius-1 ring
        self.growth_basket: float = 0.0    # food surplus stored toward the next citizen
        self.settler_cost_factor: float = 1.0  # per-civ settler cost escalation (spec 1.2)
        # City combat (M31, spec 3.3): cities are multi-turn siege objectives
        self.hp: int = 200
        self.occupied_turns: int = 0     # >0 right after capture; extra unhappiness
        self.was_attacked: bool = False  # suppresses city healing this turn

    def city_max_hp(self) -> int:
        """Walls add an HP tier (M31)."""
        return 200 + (100 if "Wall" in self.buildings else 0)

    def combat_strength(self) -> float:
        """Defense strength: scales with population and Walls (M31)."""
        strength = 10.0 + 2.0 * self.population
        if "Wall" in self.buildings:
            strength += 10.0
        return strength

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

    def food_to_grow(self) -> float:
        """Food needed in the basket for the next citizen (deep-systems
        spec 1.5, Civ-V-style decelerating curve)."""
        n = self.population
        return 15 + 8 * (n - 1) + (n - 1) ** 1.5

    def calculate_housing(self, tile_dict: Optional[Dict[tuple, Any]] = None) -> float:
        """Housing cap (deep-systems spec 1.5/1.10): base 2, +3 fresh water
        from any owned river tile, + each building's housing field
        (Granary 2, Aqueduct 4), +0.5 per improved owned tile."""
        housing = 2.0
        for b in self.buildings.values():
            housing += getattr(b, "housing", 0) or 0
        if tile_dict:
            owned = [tile_dict[p] for p in self.owned_tiles if p in tile_dict]
            if any(getattr(t, "has_river", False) for t in owned):
                housing += 3
            housing += sum(1 for t in owned if getattr(t, "improvement", None)) * 0.5
        return housing

    def grow(self, tiles: Optional[Dict[tuple, Any]] = None, growth_modifier: float = 1.0):
        """Population growth from food surplus (deep-systems spec 1.5):
        each citizen eats 2 food; surplus fills a growth basket against a
        decelerating cost curve; deficits drain the basket and then starve
        a citizen. Housing slows growth near the cap and halts it at it.
        growth_modifier scales positive surplus (empire unhappiness,
        deep-systems spec 1.6); at 0 or below, growth halts entirely."""
        yields = self.calculate_yields(tiles)
        food = yields.get("food", 0)
        surplus = food - 2.0 * self.population
        if surplus >= 0:
            if growth_modifier <= 0:
                return
            surplus *= growth_modifier
            tile_dict = None
            if tiles is not None:
                tile_dict = tiles.tiles if hasattr(tiles, 'tiles') else tiles
            housing = self.calculate_housing(tile_dict)
            if self.population >= housing:
                return
            if self.population >= housing - 1:
                surplus *= 0.5
            self.growth_basket += surplus
            cost = self.food_to_grow()
            if self.growth_basket >= cost:
                self.growth_basket -= cost
                self.population += 1
        else:
            self.growth_basket += surplus
            if self.growth_basket < 0:
                self.growth_basket = 0.0
                if self.population > 1:
                    self.population -= 1

    def initialize_borders(self):
        """Seed initial ownership: center tile plus the radius-1 ring
        (Chebyshev metric, consistent with the Mission 19 tile economy)."""
        cx, cy = self.position
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.owned_tiles.add((cx + dx, cy + dy))

    def assign_citizens(self, tile_dict: Dict[tuple, Any]) -> List[Any]:
        """Citizen assignment (deep-systems spec 1.3): the center tile is
        worked for free; each point of population works the best remaining
        owned tile (greedy by total yield). Returns the worked tiles."""
        cx, cy = self.position
        worked = []
        center = tile_dict.get((cx, cy))
        if center is not None:
            worked.append(center)
        candidates = [tile_dict[pos] for pos in self.owned_tiles
                      if pos != (cx, cy) and pos in tile_dict]
        candidates.sort(key=lambda t: -sum(t.get_yields().values()))
        worked.extend(candidates[:max(0, int(self.population))])
        return worked

    def accumulate_culture(self, tile_dict: Dict[tuple, Any], culture_output: float,
                           claimed_globally) -> Optional[tuple]:
        """Border growth (deep-systems spec 1.7): culture fills a basket; at
        the claim threshold the city claims the highest-yield tile within
        radius 3 that nobody owns yet. Returns the claimed position or None."""
        self.culture_basket += culture_output
        threshold = 10 + 6 * (self.tiles_claimed ** 1.1)
        if self.culture_basket < threshold:
            return None
        cx, cy = self.position
        best_pos, best_val = None, -1.0
        for (tx, ty), tile in tile_dict.items():
            if abs(tx - cx) > 3 or abs(ty - cy) > 3:
                continue
            pos = (tx, ty)
            if pos in self.owned_tiles or pos in claimed_globally:
                continue
            val = sum(tile.get_yields().values())
            if val > best_val:
                best_val, best_pos = val, pos
        if best_pos is None:
            return None
        self.culture_basket -= threshold
        self.owned_tiles.add(best_pos)
        self.tiles_claimed += 1
        return best_pos

    def calculate_yields(self, tiles: Optional[Dict[tuple, Any]] = None) -> Dict[str, float]:
        """Calculate total yields for the city, including adjacency bonuses."""
        # Compute adjacency if map tiles are available
        if tiles is not None:
            self.calculate_adjacency(tiles)

        if tiles is not None:
            # Handle HexMap objects (has .tiles dict) or plain dicts
            tile_dict = tiles.tiles if hasattr(tiles, 'tiles') else tiles
            # Tile economy (deep-systems spec 1.1): the city works its center
            # tile plus its `population` best nearby tiles (radius 2), so city
            # output is driven by the map instead of flat constants. Greedy
            # pick is a stand-in until citizen assignment (Mission 21).
            yields = {
                "food": 0.0,
                "gold": 0.0,
                "science": self.population * 0.5,
                "production": 0.0,
                "culture": self.population * 0.2,
                "faith": 0.0,
            }
            if not self.owned_tiles:
                self.initialize_borders()
            worked = self.assign_citizens(tile_dict)
            for tile in worked:
                for key, val in tile.get_yields().items():
                    if key in yields:
                        yields[key] += val
        else:
            # Legacy callers/tests without a map: keep the old flat baseline.
            yields = {
                "food": 2.0,
                "gold": 1.0,
                "science": self.population * 0.5,
                "production": 3.0,
                "culture": self.population * 0.2,
                "faith": 0.0,
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
                yields["faith"] = yields.get("faith", 0) + building.faith
            if hasattr(building, "culture") and building.culture > 0:
                yields["culture"] += building.culture
            if building.happiness > 0:
                self.happiness += building.happiness

        # Building percentage multipliers (deep-systems spec 1.10): flat
        # adds first (above), then the multiplicative stack, before any
        # later pipeline stages.
        pct_totals = {"production": 0.0, "gold": 0.0, "science": 0.0}
        for building in self.buildings.values():
            pct_totals["production"] += getattr(building, "production_pct", 0) or 0
            pct_totals["gold"] += getattr(building, "gold_pct", 0) or 0
            pct_totals["science"] += getattr(building, "science_pct", 0) or 0
        for key, pct in pct_totals.items():
            if pct:
                yields[key] *= (1 + pct)

        # Population bonuses
        yields["food"] += self.population * 0.5
        yields["gold"] += self.population * 0.2

        # Happiness affects production and stability
        if self.happiness < 0:
            yields["production"] *= 0.8
        elif self.happiness > 10:
            yields["production"] *= 1.1

        # Stability: city-wide metric based on happiness, buildings, districts
        stability = 50  # base stability
        for b_name in self.buildings:
            if hasattr(b_name, 'name'):
                if "Palace" in b_name.name:
                    stability += 20
                elif "Temple" in b_name.name:
                    stability += 10
                elif "Market" in b_name.name:
                    stability += 5
            else:
                if "Palace" in str(b_name):
                    stability += 20
                elif "Temple" in str(b_name):
                    stability += 10
                elif "Market" in str(b_name):
                    stability += 5
        for d_name in self.districts:
            if hasattr(d_name, 'name'):
                if d_name.name == "Government":
                    stability += 15
            else:
                if str(d_name) == "Government":
                    stability += 15
        stability += self.happiness  # happiness directly affects stability
        stability = max(0, min(100, stability))
        yields["stability"] = stability

        # Low stability causes penalties
        if stability < 20:
            yields["production"] *= 0.7
            yields["gold"] *= 0.5
        elif stability < 40:
            yields["production"] *= 0.9
            yields["gold"] *= 0.8

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

    def calculate_production_capacity(self) -> int:
        """Calculate total production capacity based on districts and buildings."""
        base = 100
        # Encampment district gives +10% production capacity
        if "Encampment" in self.districts:
            base += 20
        # Fortress district gives +20% production capacity
        if "Fortress" in self.districts:
            base += 40
        # Buildings that boost production capacity
        for building in self.buildings.values():
            if building.name == "Stable":
                base += 10
        return base

    def calculate_production(self) -> int:
        """Calculate production output for the current turn."""
        base = int(self.production_capacity * 0.1)
        # Encampment district gives +1 production
        if "Encampment" in self.districts:
            base += 1
        # Fortress district gives +2 production
        if "Fortress" in self.districts:
            base += 2
        # Buildings that boost production
        for building in self.buildings.values():
            if building.name == "Armory":
                base += 1
            elif building.name == "Weapon Workshop":
                base += 2
        return base

    def get_production_cost(self, item: str) -> Optional[int]:
        """Look up production cost from game data."""
        if item in UNIT_TYPES:
            cost = UNIT_TYPES[item].production_cost
            req = UNIT_TYPES[item].requires_tech
            if req and req in TECHNOLOGIES:
                # Era cost curve (deep-systems spec 1.11): units double in
                # cost each era past Ancient (buildings keep table costs).
                cost = int(cost * (2 ** list(Era).index(TECHNOLOGIES[req].era)))
            if item == "Settler":
                # Settler cost escalation (deep-systems spec 1.2): +30% per
                # settler this civ already produced (factor set by Game).
                cost = int(round(cost * self.settler_cost_factor))
            return cost
        if item in BUILDINGS:
            return BUILDINGS[item].production_cost
        if item in WONDERS:
            return WONDERS[item].cost
        return None

    def is_production_complete(self) -> bool:
        """Check if current production is complete."""
        if not self.current_production:
            return False
        cost = self.get_production_cost(self.current_production)
        if cost is None:
            return False
        return self.production >= cost

    def get_production_details(self) -> Dict[str, Any]:
        """Get current production details for UI display."""
        if not self.current_production:
            return {}
        cost = self.get_production_cost(self.current_production)
        if cost is None:
            return {}
        progress = min(self.production / cost, 1.0) if cost > 0 else 1.0
        return {
            "item": self.current_production,
            "cost": cost,
            "current": self.production,
            "progress": progress,
            "is_complete": progress >= 1.0,
            "capacity": self.production_capacity,
        }

    def get_buildable_units(self, researched_techs: Optional[set] = None, owned_resources: Optional[set] = None) -> List[str]:
        """Return list of unit names that this city can currently build."""
        available = []
        for uname, utype in UNIT_TYPES.items():
            # Settlers consume population (deep-systems spec 1.2): a city at
            # 1 population cannot afford to emit one.
            if uname == "Settler" and self.population < 2:
                continue
            # Check tech requirement
            if utype.requires_tech and researched_techs and utype.requires_tech not in researched_techs:
                continue
            # Check resource requirement (M32: None means "don't gate"; empty set gates)
            if utype.resource_required and owned_resources is not None and utype.resource_required not in owned_resources:
                continue
            # Check already in queue or current
            if uname in self.production_queue or uname == self.current_production:
                continue
            available.append(uname)
        return available

    def get_buildable_buildings(self, researched_techs: Optional[set] = None) -> List[str]:
        """Return list of building names that this city can currently build."""
        available = []
        for bname, btype in BUILDINGS.items():
            # Check district requirement
            if btype.requires_district:
                if btype.requires_district not in self.buildings:
                    # Check if the district itself exists
                    district_found = False
                    for existing_b in self.buildings.values():
                        if existing_b.district_type == btype.requires_district:
                            district_found = True
                            break
                    if not district_found:
                        continue
            # Check tech requirement
            if btype.requires_tech and researched_techs and btype.requires_tech not in researched_techs:
                continue
            # Check already built or in queue
            if bname in self.buildings or bname in self.production_queue or bname == self.current_production:
                continue
            available.append(bname)
        return available

    def assign_production(self, item: str, researched_techs: Optional[set] = None, owned_resources: Optional[set] = None) -> bool:
        """Assign an item to production queue with validation. Returns True if successfully assigned."""
        if item in self.production_queue or item == self.current_production:
            return False

        if item in WONDERS:
            # Wonders can only be built once globally
            if item in BUILT_WONDERS:
                return False
            wtype = WONDERS[item]
            if wtype.requires_tech and researched_techs and wtype.requires_tech not in researched_techs:
                return False
        elif item in UNIT_TYPES:
            utype = UNIT_TYPES[item]
            # Check resource requirement (M32: None means "don't gate"; empty set gates)
            if utype.resource_required and owned_resources is not None and utype.resource_required not in owned_resources:
                return False
            # Check technology requirement
            if utype.requires_tech and researched_techs and utype.requires_tech not in researched_techs:
                return False
        elif item in BUILDINGS:
            btype = BUILDINGS[item]
            if btype.requires_tech and researched_techs and btype.requires_tech not in researched_techs:
                return False

        self.production_queue.append(item)
        return True

    def process_production(self, turn_food: float, turn_gold: float, turn_science: float, turn_production: float):
        """Process one turn of city production.
        Returns the completed item name, or a (name, is_wonder) tuple for wonders."""
        self.gold += turn_gold
        self.science += turn_science
        self.production_capacity = self.calculate_production_capacity()
        self.production += turn_production

        if self.production_queue:
            item = self.production_queue[0]
            if self.current_production is None:
                self.current_production = item

            cost = self.get_production_cost(item)
            if cost is None:
                cost = 100  # fallback

            if self.production >= cost:
                if item in self.production_queue:
                    self.production_queue.remove(item)
                self.current_production = None
                # Production overflow (deep-systems spec 1.11): carry the
                # surplus into the next item, capped at one full cost.
                overflow = self.production - cost
                if self.production_queue:
                    next_cost = self.get_production_cost(self.production_queue[0])
                    cap = next_cost if next_cost is not None else cost
                else:
                    cap = cost
                self.production = max(0.0, min(overflow, cap))

                # Handle wonder completion
                if item in WONDERS:
                    self._complete_wonder(item)
                    return (item, True)

                return item

        return None

    def _complete_wonder(self, wonder_name: str):
        """Handle completion of a world wonder."""
        wtype = WONDERS[wonder_name]

        # Check if another civ already built this wonder
        if wonder_name in BUILT_WONDERS:
            # Refund 50% of wonder cost as gold
            refund = int(wtype.cost * 0.5)
            self.gold += refund
            print(f"  ⚠️ {self.owner} built {wonder_name} but another civ already has it — refunded {refund} gold")
            return

        # Mark as built globally
        BUILT_WONDERS.add(wonder_name)

        # Add as a special building
        self.buildings[wonder_name] = wtype

        # Apply effects
        effects_applied = []
        for effect_key, effect_val in wtype.effects.items():
            if effect_key == 'science_bonus':
                self.science += effect_val * 100  # Convert to flat science
                effects_applied.append(f"+{effect_val*100} science")
            elif effect_key == 'worker_speed':
                effects_applied.append(f"worker speed x{effect_val}")
            elif effect_key == 'faith_per_turn':
                self.faith += effect_val
                effects_applied.append(f"+{effect_val} faith")
            elif effect_key == 'happiness':
                self.happiness += int(effect_val)
                effects_applied.append(f"+{int(effect_val)} happiness")
            else:
                effects_applied.append(f"{effect_key} +{effect_val}")

        print(f"  🏛️ {self.owner} completed {wonder_name}: {', '.join(effects_applied)}")


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
        total = {"food": 0.0, "gold": 0.0, "science": 0.0, "production": 0.0, "culture": 0.0, "faith": 0.0, "stability": 0.0}

        for city in self.get_cities_by_owner(owner):
            yields = city.calculate_yields(tiles)
            for stat, value in yields.items():
                total[stat] += value

        return total
