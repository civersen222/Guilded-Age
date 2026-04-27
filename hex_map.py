"""
CivKings - Hexagonal Map System
Generates and manages the hex grid world map
"""
import random
import math
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from game_data import TerrainType, TERRAIN_YIELDS, TERRAIN_MOVEMENT_COST, ResourceType, TERRAIN_RESOURCE_COMPATIBILITY, RESOURCE_YIELDS, RiverNetwork


class HexTile:
    """Represents a single hex tile on the map"""
    
    def __init__(self, x: int, y: int, terrain: TerrainType):
        self.x = x
        self.y = y
        self.terrain = terrain
        self.resource: Optional[ResourceType] = None
        self.resource_yield: Dict[str, float] = {}
        self.has_river: bool = False
        self.city: Optional[str] = None  # name of city if present
        self.unit: Optional[str] = None  # name of unit if present
        self.visited: bool = False
        self.explored: bool = False
        
    def get_yields(self) -> Dict[str, float]:
        """Get base yields for this tile"""
        yields = dict(TERRAIN_YIELDS.get(self.terrain, {"food": 0, "production": 0, "gold": 0, "science": 0}))
        if self.resource and self.resource in RESOURCE_YIELDS:
            res_yield = RESOURCE_YIELDS[self.resource]
            for key in ["food", "production", "gold", "science", "faith", "happiness"]:
                yields[key] = yields.get(key, 0) + getattr(res_yield, key, 0)
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
        self.fog = FogOfWar()

    def generate(self):
        """Generate the map with random terrain."""
        for x in range(self.width):
            for y in range(self.height):
                terrain = self._random_terrain(x, y)
                tile = HexTile(x, y, terrain)
                self.tiles[(x, y)] = tile
                self.fog.tiles[(x, y)] = tile
        self._place_resources()
        self._generate_rivers()

    def _generate_rivers(self):
        """Generate rivers using RiverNetwork."""
        river_net = RiverNetwork(self.width, self.height)
        self.rivers = river_net.generate_rivers(self.tiles, num_rivers=4)

    def _random_terrain(self, x: int, y: int) -> TerrainType:
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
        weights = [0.3, 0.25, 0.15, 0.1, 0.05, 0.05, 0.03, 0.04, 0.03]
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
                if tile and (tx, ty) in self.fog.discovered:
                    if tile.city:
                        row.append("C")
                    elif tile.unit:
                        row.append("U")
                    else:
                        row.append(terrain_chars.get(tile.terrain, "."))
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
        self.noise = SimplexNoise2D(seed=random.randint(0, 99999))
        self.continents: List[Continent] = []

    def generate_continents(self) -> Dict[Tuple[int, int], TerrainType]:
        """Generate continent-based terrain map. Returns {(x,y): terrain_type}."""
        elevation_map = self._generate_elevation_map()
        land_tiles = {(x, y) for x, y in elevation_map if elevation_map[(x, y)] > 0.35}
        self.continents = self._find_continents(land_tiles)
        terrain_map = self._assign_terrain_from_elevation(elevation_map)
        self._validate_starting_positions(terrain_map)
        self._fix_landlocked_tiles(terrain_map)
        return terrain_map

    def _generate_elevation_map(self) -> Dict[Tuple[int, int], float]:
        """Generate elevation using multi-octave noise."""
        scale = max(self.width, self.height) / 4
        elevation_map: Dict[Tuple[int, int], float] = {}

        for x in range(self.width):
            for y in range(self.height):
                nx, ny = x / scale, y / scale
                val = self.noise.octave_noise(nx, ny, octaves=5, persistence=0.6)
                val = (val + 1) / 2
                val = max(0, min(1, val))
                elevation_map[(x, y)] = val

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

            if len(continent_tiles) >= 3:
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

            if not on_continent or elevation < 0.35:
                if elevation < 0.2:
                    terrain_map[(x, y)] = TerrainType.OCEAN
                else:
                    terrain_map[(x, y)] = TerrainType.WATER_COAST
            elif elevation < 0.45:
                terrain_map[(x, y)] = TerrainType.PLAINS
            elif elevation < 0.55:
                terrain_map[(x, y)] = TerrainType.GRASSLAND
            elif elevation < 0.65:
                terrain_map[(x, y)] = TerrainType.HILLS
            elif elevation < 0.75:
                terrain_map[(x, y)] = TerrainType.FOREST
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
                        if count >= 3 and most_common != current:
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
        # Generate continent-based terrain
        num_continents = max(2, min(5, (self.width * self.height) // 100))
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
