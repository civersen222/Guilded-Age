"""
CivKings - Hexagonal Map System
Generates and manages the hex grid world map
"""
import random
import math
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from game_data import TerrainType, TERRAIN_YIELDS, TERRAIN_MOVEMENT_COST, ResourceType, TERRAIN_RESOURCE_COMPATIBILITY, RESOURCE_YIELDS, RiverNetwork, ClimateZone, CLIMATE_MODIFIERS, get_climate_for_row, LandmarkType, LANDMARKS


class HexTile:
    """Represents a single hex tile on the map"""
    
    def __init__(self, x: int, y: int, terrain: TerrainType):
        self.x = x
        self.y = y
        self.terrain = terrain
        self.climate_zone: ClimateZone = ClimateZone.TEMPERATE
        self.resource: Optional[ResourceType] = None
        self.resource_yield: Dict[str, float] = {}
        self.has_river: bool = False
        self.city: Optional[str] = None  # name of city if present
        self.unit: Optional[str] = None  # name of unit if present
        self.visited: bool = False
        self.explored: bool = False
        self.landmark: Optional[LandmarkType] = None
        self.landmark_discovered: bool = False
        self.improvement: Optional[str] = None  # improvement type (e.g. 'Farm', 'Mine')
        self.improvement_progress: int = 0  # 0 = not started, -1 = complete
        
    def get_yields(self) -> Dict[str, float]:
        """Get base yields for this tile"""
        from improvements import IMPROVEMENTS
        yields = dict(TERRAIN_YIELDS.get(self.terrain, {"food": 0, "production": 0, "gold": 0, "science": 0}))
        if self.resource and self.resource in RESOURCE_YIELDS:
            res_yield = RESOURCE_YIELDS[self.resource]
            for key in ["food", "production", "gold", "science", "faith", "happiness"]:
                yields[key] = yields.get(key, 0) + getattr(res_yield, key, 0)
        # Add improvement yields if completed
        if self.improvement and self.improvement_progress == -1:
            imp = IMPROVEMENTS.get(self.improvement)
            if imp:
                for key, val in imp.get("yields", {}).items():
                    yields[key] = yields.get(key, 0) + val
        return yields
    
    def __repr__(self):
        terrain_char = {
            TerrainType.PLAINS: "·",
            TerrainType.GRASSLAND: "·",
            TerrainType.FOREST: "F",
            TerrainType.HILLS: "^",
            TerrainType.MOUNTAIN: "▲",
            TerrainType.DESERT: "·",
            TerrainType.TUNDRA: "·",
            TerrainType.WATER_COAST: "~",
            TerrainType.OCEAN: "≈",
        }
        char = terrain_char.get(self.terrain, "?")
        if self.city:
            char = "C"
        elif self.unit:
            char = "U"
        elif self.resource:
            char = "R"
        return f"HexTile({self.x},{self.y})={char}"


class ExponentialFogOfWar:
    """Manages fog of war with exponential visibility decay.
    
    Visibility decays exponentially with distance from cities/units:
    - Tiles within a city's vision radius are fully visible
    - Beyond that, visibility decreases with distance
    - Mountains can block line of sight
    - 'Explored' tiles show terrain even when not currently visible
    """
    
    def __init__(self, decay_rate: float = 2.0):
        self.explored: Set[Tuple[int, int]] = set()      # Tiles ever seen
        self.visible: Set[Tuple[int, int]] = set()        # Tiles currently visible
        self.visibility: Dict[Tuple[int, int], float] = {}  # Intensity 0.0-1.0
        self.decay_rate = decay_rate
        self.city_vision_radius: int = 3
        self.unit_vision_radius: int = 2
        self.tiles: Dict[Tuple[int, int], 'HexTile'] = {}
    
    def set_tiles(self, tiles: Dict[Tuple[int, int], 'HexTile']):
        """Set the tile grid for terrain checks."""
        self.tiles = tiles
    
    def calculate_visibility_from_city(self, city_x: int, city_y: int, radius: int = None) -> Set[Tuple[int, int]]:
        """Calculate visibility from a city center."""
        radius = radius or self.city_vision_radius
        visible = set()
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                dist = max(abs(dx), abs(dy), abs(dx + dy))
                if dist <= radius:
                    tx, ty = city_x + dx, city_y + dy
                    if self._is_visible_from(tx, ty, city_x, city_y, dist, radius):
                        visible.add((tx, ty))
        return visible
    
    def calculate_visibility_from_unit(self, unit_x: int, unit_y: int, radius: int = None) -> Set[Tuple[int, int]]:
        """Calculate visibility from a unit."""
        radius = radius or self.unit_vision_radius
        visible = set()
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                dist = max(abs(dx), abs(dy), abs(dx + dy))
                if dist <= radius:
                    tx, ty = unit_x + dx, unit_y + dy
                    if self._is_visible_from(tx, ty, unit_x, unit_y, dist, radius):
                        visible.add((tx, ty))
        return visible
    
    def _is_visible_from(self, target_x: int, target_y: int, source_x: int, source_y: int, dist: int, radius: int) -> bool:
        """Check if a tile is visible from a source, considering terrain."""
        tile = self.tiles.get((target_x, target_y))
        if not tile:
            return False
        
        # Check line of sight - mountains can block vision
        if dist > 1:
            if self._is_line_of_sight_blocked(target_x, target_y, source_x, source_y):
                return False
        
        # Exponential decay of visibility
        visibility = 1.0 / (1.0 + (dist ** 2) / (2 * self.decay_rate))
        return visibility > 0.1
    
    def _is_line_of_sight_blocked(self, target_x: int, target_y: int, source_x: int, source_y: int) -> bool:
        """Check if line of sight is blocked by mountains."""
        dx, dy = target_x - source_x, target_y - source_y
        dist = max(abs(dx), abs(dy), abs(dx + dy))
        
        # Check intermediate tiles for mountains
        for d in range(1, dist):
            check_x = source_x + int(dx * d / dist)
            check_y = source_y + int(dy * d / dist)
            check_tile = self.tiles.get((check_x, check_y))
            if check_tile and check_tile.terrain == TerrainType.MOUNTAIN:
                return True
        return False
    
    def update_visibility(self, sources: List[Tuple[int, int, int]]) -> None:
        """Update visibility from multiple sources.
        
        sources: list of (x, y, radius) tuples for cities/units
        """
        self.visible.clear()
        self.visibility.clear()
        
        for sx, sy, radius in sources:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    dist = max(abs(dx), abs(dy), abs(dx + dy))
                    if dist > radius:
                        continue
                    
                    tx, ty = sx + dx, sy + dy
                    if (tx, ty) not in self.tiles:
                        continue
                    
                    if self._is_visible_from(tx, ty, sx, sy, dist, radius):
                        self.visible.add((tx, ty))
                        # Exponential decay
                        intensity = 1.0 / (1.0 + (dist ** 2) / self.decay_rate)
                        self.visibility[(tx, ty)] = intensity
                        self.explored.add((tx, ty))
    
    def is_visible(self, x: int, y: int) -> bool:
        """Check if a tile is currently visible."""
        return (x, y) in self.visible
    
    def is_explored(self, x: int, y: int) -> bool:
        """Check if a tile has been explored (seen before)."""
        return (x, y) in self.explored
    
    def get_visibility_intensity(self, x: int, y: int) -> float:
        """Get visibility intensity for a tile (0.0 to 1.0)."""
        return self.visibility.get((x, y), 0.0)
    
    def clear(self):
        """Clear current visibility (keep explored)."""
        self.visible.clear()
        self.visibility.clear()
    
    def reset_fog(self):
        """Reset all fog (start fresh)."""
        self.explored.clear()
        self.visible.clear()
        self.visibility.clear()


class FogOfWar:
    """Manages fog of war (discovered vs visible tiles)."""

    def __init__(self):
        self.tiles: Dict[Tuple[int, int], HexTile] = {}
        self.discovered: Set[Tuple[int, int]] = set()

    def is_visible(self, x: int, y: int) -> bool:
        return (x, y) in self.discovered

    def set_discovered(self, x: int, y: int):
        self.discovered.add((x, y))

    def discover(self, x: int, y: int):
        self.discovered.add((x, y))

    def clear(self):
        self.discovered.clear()


class WorldMap:
    """Base world map with tiles, fog of war, and rendering."""

    def __init__(self, width: int = 16, height: int = 16):
        self.width = width
        self.height = height
        self.tiles: Dict[Tuple[int, int], HexTile] = {}
        self.fog = ExponentialFogOfWar()

    def generate(self):
        """Generate the map with random terrain, climate-aware."""
        for x in range(self.width):
            for y in range(self.height):
                climate = get_climate_for_row(y, self.height)
                terrain = self._random_terrain(x, y, climate)
                tile = HexTile(x, y, terrain)
                tile.climate_zone = climate
                self.tiles[(x, y)] = tile
        self.fog.set_tiles(self.tiles)
        self._place_resources()
        self._place_landmarks()
        self._generate_rivers()

    def _place_landmarks(self):
        """Place discoverable landmarks on the map."""
        suitable_tiles = [t for t in self.tiles.values() 
                         if t.terrain not in (TerrainType.MOUNTAIN, TerrainType.OCEAN) 
                         and not t.city]
        for landmark_type in LandmarkType:
            if random.random() < 0.3 and suitable_tiles:
                tile = random.choice(suitable_tiles)
                tile.landmark = landmark_type
                suitable_tiles.remove(tile)

    def _generate_rivers(self):
        """Generate rivers using RiverNetwork."""
        river_net = RiverNetwork(self.width, self.height)
        self.rivers = river_net.generate_rivers(self.tiles, num_rivers=4)

    def _terrain_weights_for_climate(self, climate: ClimateZone) -> List[float]:
        """Return terrain weights biased by climate zone."""
        weights = {
            ClimateZone.TEMPERATE: [0.30, 0.25, 0.15, 0.10, 0.05, 0.05, 0.03, 0.04, 0.03],
            ClimateZone.TROPICAL:   [0.35, 0.35, 0.20, 0.02, 0.00, 0.00, 0.00, 0.05, 0.03],
            ClimateZone.ARID:       [0.10, 0.05, 0.02, 0.00, 0.00, 0.00, 0.70, 0.04, 0.09],
            ClimateZone.COLD:       [0.15, 0.10, 0.20, 0.15, 0.05, 0.00, 0.00, 0.05, 0.30],
            ClimateZone.POLAR:      [0.02, 0.02, 0.01, 0.02, 0.03, 0.00, 0.00, 0.01, 0.89],
        }
        key = list(weights.keys())[list(ClimateZone).index(climate)]
        return weights[key]

    def _random_terrain(self, x: int, y: int, climate: ClimateZone) -> TerrainType:
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.tiles:
                    neighbors.append(self.tiles[(nx, ny)].terrain)
        if neighbors and random.random() < 0.6:
            return random.choice(neighbors)
        terrains = list(TERRAIN_YIELDS.keys())
        weights = self._terrain_weights_for_climate(climate)
        return random.choices(terrains, weights=weights, k=1)[0]

    def _place_resources(self):
        """Place resources on the map using terrain compatibility map."""
        for tile in self.tiles.values():
            compatible_resources = TERRAIN_RESOURCE_COMPATIBILITY.get(tile.terrain, [])
            if compatible_resources and random.random() < 0.15:
                tile.resource = random.choice(compatible_resources)
                if tile.resource in RESOURCE_YIELDS:
                    res_yield = RESOURCE_YIELDS[tile.resource]
                    tile.resource_yield = {
                        "food": res_yield.food,
                        "production": res_yield.production,
                        "gold": res_yield.gold,
                        "science": res_yield.science,
                        "faith": res_yield.faith,
                        "happiness": res_yield.happiness,
                    }

    def get_tile(self, x: int, y: int) -> Optional[HexTile]:
        return self.tiles.get((x, y))

    def get_neighbors(self, x: int, y: int) -> List[HexTile]:
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.tiles:
                    neighbors.append(self.tiles[(nx, ny)])
        return neighbors

    def display(self, center_x: int, center_y: int, radius: int = 5) -> str:
        terrain_chars = {
            TerrainType.PLAINS: ".", TerrainType.GRASSLAND: ".",
            TerrainType.FOREST: "F", TerrainType.HILLS: "^",
            TerrainType.MOUNTAIN: "#", TerrainType.DESERT: ":",
            TerrainType.TUNDRA: "~", TerrainType.WATER_COAST: "-",
            TerrainType.OCEAN: "~",
        }
        lines = []
        for dy in range(-radius, radius + 1):
            row = []
            for dx in range(-radius, radius + 1):
                tx, ty = center_x + dx, center_y + dy
                tile = self.tiles.get((tx, ty))
                if tile and self.fog.is_explored(tx, ty):
                    if tile.city:
                        row.append("C" if self.fog.is_visible(tx, ty) else "c")
                    elif tile.unit and self.fog.is_visible(tx, ty):
                        row.append("U")
                    elif tile.resource:
                        row.append("R" if self.fog.is_visible(tx, ty) else "?")
                    else:
                        row.append(terrain_chars.get(tile.terrain, ".") if self.fog.is_visible(tx, ty) else "?")
                else:
                    row.append("?")
            lines.append(" ".join(row))
        return "\n".join(lines)


# ── Section 1.2: Continent Generation and Terrain Smoothing ──


class SimplexNoise2D:
    """Minimal 2D noise generator for terrain/continent generation."""

    def __init__(self, seed: int = 0):
        self.perm = list(range(256))
        random.seed(seed)
        random.shuffle(self.perm)
        self.perm += self.perm

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        h = hash_val & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x: float, y: float) -> float:
        X, Y = int(math.floor(x)), int(math.floor(y))
        x -= X
        y -= Y
        fx, fy = self._fade(x), self._fade(y)
        n00 = self._grad(self.perm[X + self.perm[Y]], x, y)
        n10 = self._grad(self.perm[X + 1 + self.perm[Y]], x - 1, y)
        n01 = self._grad(self.perm[X + self.perm[Y + 1]], x, y - 1)
        n11 = self._grad(self.perm[X + 1 + self.perm[Y + 1]], x - 1, y - 1)
        nx0 = self._lerp(n00, n10, fx)
        nx1 = self._lerp(n01, n11, fx)
        return self._lerp(nx0, nx1, fy)

    def octave_noise(self, x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2
        return total / max_value


@dataclass
class Continent:
    """A contiguous landmass on the map."""
    id: int
    center: Tuple[int, int]
    tiles: Set[Tuple[int, int]]
    name: str


class ContinentGenerator:
    """Generate continents using noise-based continent algorithm (1.2.1)."""

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

    def __init__(self, map_width: int, map_height: int, num_continents: int = 3):
        self.width = map_width
        self.height = map_height
        self.num_continents = num_continents
        self.continents: List[Continent] = []
        self.continent_centers: List[Tuple[int, int]] = []

    def generate_continents(self) -> Dict[Tuple[int, int], TerrainType]:
        """Generate continent-based terrain map. Returns {(x,y): terrain_type}."""
        self.continent_centers = self._place_continent_centers()
        elevation_map = self._generate_elevation_map()
        land_tiles = {(x, y) for x, y in elevation_map if elevation_map[(x, y)] > 0.35}
        self.continents = self._find_continents(land_tiles)
        terrain_map = self._assign_terrain_from_elevation(elevation_map)
        self._validate_starting_positions(terrain_map)
        self._fix_landlocked_tiles(terrain_map)
        return terrain_map

    def _place_continent_centers(self) -> List[Tuple[int, int]]:
        """Place continent centers at well-separated positions, well from edges."""
        centers = []
        margin = int(max(self.width, self.height) * 0.15)
        boost_radius = max(self.width, self.height) / (self.num_continents * 0.75)
        min_dist = boost_radius * 1.6  # Ensure continents don't overlap
        attempts = 0

        for _ in range(self.num_continents):
            for _ in range(200):
                cx = random.randint(margin, self.width - margin)
                cy = random.randint(margin, self.height - margin)
                if all(math.dist((cx, cy), (ox, oy)) >= min_dist for ox, oy in centers):
                    centers.append((cx, cy))
                    break
                attempts += 1
            if not centers or len(centers) < self.num_continents:
                # Fallback: grid placement
                cols = min(self.num_continents, 3)
                rows = max(1, self.num_continents // cols)
                for r in range(rows):
                    for c in range(cols):
                        if len(centers) >= self.num_continents:
                            break
                        cx = int((c + 0.5) * self.width / cols)
                        cy = int((r + 0.5) * self.height / rows)
                        cx = max(margin, min(self.width - margin, cx))
                        cy = max(margin, min(self.height - margin, cy))
                        centers.append((cx, cy))
                    if len(centers) >= self.num_continents:
                        break

        return centers[:self.num_continents]

    def _generate_elevation_map(self) -> Dict[Tuple[int, int], float]:
        """Generate elevation using continent-centered island creation."""
        elevation_map: Dict[Tuple[int, int], float] = {}
        base_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        detail_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        scale = max(self.width, self.height) / 5

        # Start with uniform low base elevation (mostly ocean)
        for x in range(self.width):
            for y in range(self.height):
                # Very subtle base noise - mostly flat ocean
                nx, ny = x / (scale * 4), y / (scale * 4)
                val = base_noise.octave_noise(nx, ny, octaves=2, persistence=0.4)
                val = (val + 1) / 2  # [0,1]
                # Keep base very low and uniform - most tiles will be ocean
                val = 0.08 + val * 0.08  # base range [0.08, 0.16]
                elevation_map[(x, y)] = val

        # Add continent islands
        boost_radius = max(self.width, self.height) / (self.num_continents * 1.5)

        for x in range(self.width):
            for y in range(self.height):
                current = elevation_map[(x, y)]
                best_boost = 0.0

                for cx, cy in self.continent_centers:
                    dx, dy = x - cx, y - cy
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < boost_radius:
                        t = dist / boost_radius
                        # Island shape: gentle cubic falloff for flat tops
                        falloff = 1.0 - t * t * t  # cubic falloff

                        # Multi-layer noise for elevation variation within island
                        # Layer 1: large-scale variation (determines broad regions)
                        large = base_noise.octave_noise(x / scale * 1.5, y / scale * 1.5, octaves=3, persistence=0.5)
                        large = (large + 1) / 2  # [0,1]

                        # Layer 2: fine-scale variation (adds detail)
                        fine = detail_noise.octave_noise(x / scale * 4, y / scale * 4, octaves=4, persistence=0.6)
                        fine = (fine + 1) / 2  # [0,1]

                        # Combine layers for varied elevation:
                        base_elev = large * 0.60 + 0.35  # [0.35, 0.95]
                        detail = fine * 0.20 - 0.10  # [-0.10, +0.10]
                        elevation = (base_elev + detail) * falloff + current * (1 - falloff)

                        if elevation > best_boost:
                            best_boost = elevation

                # If far from all continent centers, keep base ocean elevation
                elevation_map[(x, y)] = max(current, min(best_boost, 1.0))

        return elevation_map

    def _find_continents(self, land_tiles: Set[Tuple[int, int]]) -> List[Continent]:
        """Find contiguous landmasses via flood fill."""
        visited: Set[Tuple[int, int]] = set()
        continents: List[Continent] = []
        continent_id = 0

        for start in land_tiles:
            if start in visited:
                continue
            queue = [start]
            continent_tiles: Set[Tuple[int, int]] = set()
            while queue:
                pos = queue.pop(0)
                if pos in visited or pos not in land_tiles:
                    continue
                visited.add(pos)
                continent_tiles.add(pos)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                    neighbor = (pos[0] + dx, pos[1] + dy)
                    if neighbor in land_tiles and neighbor not in visited:
                        queue.append(neighbor)

            if len(continent_tiles) >= 20:
                center = (
                    sum(p[0] for p in continent_tiles) // len(continent_tiles),
                    sum(p[1] for p in continent_tiles) // len(continent_tiles),
                )
                continents.append(Continent(id=continent_id, center=center, tiles=continent_tiles, name=f"Continent {continent_id + 1}"))
                continent_id += 1

        self.continents = continents
        return continents

    def _assign_terrain_from_elevation(self, elevation_map: Dict[Tuple[int, int], float]) -> Dict[Tuple[int, int], TerrainType]:
        """Assign terrain types based on elevation and continent membership."""
        terrain_map: Dict[Tuple[int, int], TerrainType] = {}

        for (x, y), elevation in elevation_map.items():
            on_continent = any((x, y) in c.tiles for c in self.continents)

            if not on_continent:
                if elevation < 0.15:
                    terrain_map[(x, y)] = TerrainType.OCEAN
                else:
                    terrain_map[(x, y)] = TerrainType.WATER_COAST
            elif elevation < 0.35:
                # Below land threshold but on continent - coastal water
                terrain_map[(x, y)] = TerrainType.WATER_COAST
            elif elevation < 0.45:
                terrain_map[(x, y)] = TerrainType.PLAINS
            elif elevation < 0.55:
                terrain_map[(x, y)] = TerrainType.GRASSLAND
            elif elevation < 0.63:
                terrain_map[(x, y)] = TerrainType.HILLS
            elif elevation < 0.70:
                terrain_map[(x, y)] = TerrainType.FOREST
            elif elevation < 0.78:
                terrain_map[(x, y)] = TerrainType.DESERT
            elif elevation < 0.85:
                terrain_map[(x, y)] = TerrainType.TUNDRA
            else:
                terrain_map[(x, y)] = TerrainType.MOUNTAIN

        return terrain_map

    def _validate_starting_positions(self, terrain_map: Dict[Tuple[int, int], TerrainType]):
        """Ensure land tiles have adequate adjacent land for city placement."""
        land_terrains = {TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.FOREST, TerrainType.HILLS}
        
        for continent in self.continents:
            if len(continent.tiles) < 10:
                continue
            valid_starts = []
            for pos in continent.tiles:
                land_neighbors = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                   if (pos[0] + dx, pos[1] + dy) in continent.tiles)
                if land_neighbors >= 3:
                    valid_starts.append(pos)
            
            if not valid_starts:
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        candidate = (continent.center[0] + dx, continent.center[1] + dy)
                        if candidate not in terrain_map or terrain_map[candidate] == TerrainType.OCEAN:
                            terrain_map[candidate] = TerrainType.PLAINS
                            continent.tiles.add(candidate)

    def _fix_landlocked_tiles(self, terrain_map: Dict[Tuple[int, int], TerrainType]):
        """Ensure continents have coastline access where possible."""
        for continent in self.continents:
            has_coast = any(
                terrain_map.get((x, y)) in (TerrainType.WATER_COAST, TerrainType.OCEAN)
                for x, y in continent.tiles
            )
            if not has_coast and len(continent.tiles) > 10:
                edge_tiles = []
                for x, y in continent.tiles:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = (x + dx, y + dy)
                        if neighbor not in terrain_map or terrain_map[neighbor] in (TerrainType.OCEAN,):
                            edge_tiles.append((x, y))
                            break
                if edge_tiles:
                    edge = random.choice(edge_tiles)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        neighbor = (edge[0] + dx, edge[1] + dy)
                        if neighbor not in terrain_map:
                            terrain_map[neighbor] = TerrainType.WATER_COAST
                            continent.tiles.add(neighbor)


class TerrainSmoothing:
    """Apply smoothing passes to reduce terrain fragmentation (1.2.2)."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def smooth(self, terrain_map: Dict[Tuple[int, int], TerrainType], passes: int = 2) -> Dict[Tuple[int, int], TerrainType]:
        """Apply terrain smoothing passes. Preserves natural boundaries."""
        smoothed = dict(terrain_map)

        for _ in range(passes):
            for x in range(self.width):
                for y in range(self.height):
                    pos = (x, y)
                    neighbors = self._get_neighbors(pos)
                    if not neighbors:
                        continue

                    current = smoothed[pos]
                    terrain_counts: Dict[TerrainType, int] = {}
                    for n_pos in neighbors:
                        if n_pos in smoothed:
                            t = smoothed[n_pos]
                            terrain_counts[t] = terrain_counts.get(t, 0) + 1

                    if terrain_counts:
                        most_common = max(terrain_counts, key=terrain_counts.get)
                        count = terrain_counts[most_common]
                        # Only change if majority of neighbors agree (5+ out of 8)
                        if count >= 5 and most_common != current:
                            if most_common == TerrainType.MOUNTAIN and current not in (TerrainType.MOUNTAIN, TerrainType.HILLS):
                                smoothed[pos] = most_common
                            elif most_common != TerrainType.MOUNTAIN:
                                smoothed[pos] = most_common

        return smoothed

    def _get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get valid neighbor positions."""
        x, y = pos
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbors.append((nx, ny))
        return neighbors


class HexMap:
    """Manages the hex grid world map with continent generation and terrain smoothing (Phase 1.2)."""
    
    def __init__(self, map_width: int, map_height: int):
        self.width = map_width
        self.height = map_height
        self.tiles: Dict[Tuple[int, int], HexTile] = {}
        self.continents: List[Continent] = []
        self.terrain_map: Dict[Tuple[int, int], TerrainType] = {}
        
    def generate_map(self, seed: int = 0):
        """Generate the map with continent-based terrain and smoothing (1.2)."""
        if seed:
            random.seed(seed)
        self.generate()
    
    def generate(self):
        """Generate the map with continent-based terrain and smoothing."""
        # Generate continent-based terrain - scale with map size, cap at 3 for small maps
        map_area = self.width * self.height
        num_continents = max(2, min(3, map_area // 600))
        continent_gen = ContinentGenerator(self.width, self.height, num_continents)
        self.terrain_map = continent_gen.generate_continents()
        self.continents = continent_gen.continents

        # Apply terrain smoothing
        smoother = TerrainSmoothing(self.width, self.height)
        self.terrain_map = smoother.smooth(self.terrain_map, passes=2)

        # Create tile objects
        for x in range(self.width):
            for y in range(self.height):
                terrain = self.terrain_map.get((x, y), TerrainType.OCEAN)
                tile = HexTile(x, y, terrain)
                self.tiles[(x, y)] = tile

        # Place resources
        self._place_resources()
    
    def _place_resources(self):
        """Place resources on the map using terrain compatibility map."""
        for tile in self.tiles.values():
            compatible_resources = TERRAIN_RESOURCE_COMPATIBILITY.get(tile.terrain, [])
            if compatible_resources and random.random() < 0.15:
                tile.resource = random.choice(compatible_resources)
                if tile.resource in RESOURCE_YIELDS:
                    res_yield = RESOURCE_YIELDS[tile.resource]
                    tile.resource_yield = {
                        "food": res_yield.food,
                        "production": res_yield.production,
                        "gold": res_yield.gold,
                        "science": res_yield.science,
                        "faith": res_yield.faith,
                        "happiness": res_yield.happiness,
                    }
    
    def get_tile(self, x: int, y: int) -> Optional[HexTile]:
        """Get a tile by coordinates"""
        return self.tiles.get((x, y))
    
    def get_neighbors(self, x: int, y: int) -> List[HexTile]:
        """Get neighboring tiles (including diagonals for simplicity)"""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.tiles:
                    neighbors.append(self.tiles[(nx, ny)])
        return neighbors
    
    def get_distance(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Calculate hex distance between two points"""
        return max(abs(x2 - x1), abs(y2 - y1))
    
    def get_terrain_at(self, x: int, y: int) -> Optional[TerrainType]:
        """Get terrain type at coordinates"""
        tile = self.tiles.get((x, y))
        return tile.terrain if tile else None
    
    def get_territory(self, owner: str) -> List[HexTile]:
        """Get all tiles owned by a civilization (via cities)"""
        return [tile for tile in self.tiles.values() if tile.city and self._get_city_owner(tile.city) == owner]
    
    def _get_city_owner(self, city_name: str) -> str:
        """Get owner of a city by name"""
        return ""
    
    def display(self, view_center: Tuple[int, int], view_radius: int = 5) -> str:
        """Display the map with a view centered on the given point"""
        cx, cy = view_center
        display = []
        
        terrain_chars = {
            TerrainType.PLAINS: "·",
            TerrainType.GRASSLAND: "·",
            TerrainType.FOREST: "F",
            TerrainType.HILLS: "^",
            TerrainType.MOUNTAIN: "▲",
            TerrainType.DESERT: "·",
            TerrainType.TUNDRA: "·",
            TerrainType.WATER_COAST: "~",
            TerrainType.OCEAN: "≈",
        }
        
        for dy in range(-view_radius, view_radius + 1):
            row = []
            for dx in range(-view_radius, view_radius + 1):
                tx, ty = cx + dx, cy + dy
                tile = self.tiles.get((tx, ty))
                if tile:
                    if tile.city:
                        row.append("C")
                    elif tile.unit:
                        row.append("U")
                    elif tile.explored:
                        row.append(terrain_chars.get(tile.terrain, "."))
                    elif tile.visited:
                        row.append(".")
                    else:
                        row.append("?")
                else:
                    row.append("?")
            display.append(" ".join(row))
        
        return "\n".join(display)

    def get_starting_tile(self) -> Tuple[int, int]:
        """Get a random tile for the player's starting position with adequate resources."""
        land_terrains = {TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.FOREST, TerrainType.HILLS}
        land_tiles = [(x, y) for (x, y), t in self.terrain_map.items() if t in land_terrains]

        valid_starts = []
        for x, y in land_tiles:
            land_neighbors = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                               if (x + dx, y + dy) in self.terrain_map and self.terrain_map[(x + dx, y + dy)] in land_terrains)
            if land_neighbors >= 3:
                valid_starts.append((x, y))

        if valid_starts:
            return random.choice(valid_starts)
        elif land_tiles:
            return random.choice(land_tiles)
        return (0, 0)

    def add_city(self, city) -> None:
        """Add a city to the map"""
        city.position = self.get_starting_tile()
        self.tiles[(city.position[0], city.position[1])].city = city.name

    def add_unit(self, unit) -> None:
        """Add a unit to the map"""
        unit.position = self.get_starting_tile()
        self.tiles[(unit.position[0], unit.position[1])].unit = unit.unit_type
