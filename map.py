"""Hex map, terrain, resources, fog of war."""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import random
from hex_map import WorldMap, HexTile, TerrainType, FogOfWar
from game_data import MAP_WEIGHTS, RESOURCE_WEIGHTS, ResourceType, TERRAIN_MOVEMENT_COST, TERRAIN_RESOURCE_COMPATIBILITY


@dataclass
class ResourceNode:
    resource: ResourceType
    tile: Tuple[int, int]
    discovered: bool = False


class ImprovedFogOfWar(FogOfWar):
    """Fog of war with visibility radius based on cities and units."""

    def __init__(self):
        super().__init__()
        self.visible: Set[Tuple[int, int]] = set()
        self.city_radii: Dict[Tuple[int, int], int] = {}  # city_pos -> radius
        self.unit_radii: Dict[Tuple[int, int], int] = {}  # unit_pos -> radius

    def is_visible(self, q: int, r: int) -> bool:
        """Override base class to check visible set instead of discovered."""
        return (q, r) in self.visible

    def update_visibility(self):
        """Recalculate visible tiles from all sources."""
        self.visible.clear()
        all_sources = {}
        all_sources.update(self.city_radii)
        all_sources.update(self.unit_radii)
        for pos, radius in all_sources.items():
            q, r = pos
            for dq in range(-radius, radius + 1):
                for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                    nq, nr = q + dq, r + dr
                    if (nq, nr) in self.tiles:
                        self.visible.add((nq, nr))
                        self.discovered.add((nq, nr))

    def set_city_view(self, pos: Tuple[int, int], radius: int = 3):
        self.city_radii[pos] = radius

    def set_unit_view(self, pos: Tuple[int, int], radius: int = 2):
        self.unit_radii[pos] = radius

    def clear_unit_view(self, pos: Tuple[int, int]):
        self.unit_radii.pop(pos, None)


class ImprovedMap(WorldMap):
    """Extended map with resources, rivers, and landmarks."""

    def __init__(self):
        super().__init__()
        self.resources: Dict[Tuple[int, int], ResourceType] = {}
        self.rivers: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        self.landmarks: Dict[Tuple[int, int], str] = {}
        self._generate_resources()
        self._generate_rivers()
        self._generate_landmarks()

    def _generate_resources(self):
        """Place resources on tiles based on terrain compatibility."""
        for (q, r), tile in self.tiles.items():
            compatible_resources = TERRAIN_RESOURCE_COMPATIBILITY.get(tile.terrain, [])
            if compatible_resources and random.random() < 0.15:
                self.resources[(q, r)] = random.choice(compatible_resources)

    def _generate_rivers(self):
        """Generate a few rivers flowing from mountains."""
        mountains = [(q, r) for (q, r), t in self.tiles.items()
                      if t.terrain_type == TerrainType.MOUNTAIN]
        for _ in range(min(3, len(mountains) // 3)):
            if not mountains:
                break
            start = random.choice(mountains)
            path = [start]
            current = start
            visited = {start}
            for _ in range(5):
                neighbors = self.get_neighbors(*current)
                valid = [n for n in neighbors if n not in visited
                         and self.get_tile(*n).terrain_type != TerrainType.MOUNTAIN]
                if not valid:
                    break
                current = random.choice(valid)
                path.append(current)
                visited.add(current)
                if self.get_tile(*current).terrain_type == TerrainType.WATER_COAST:
                    break
            if len(path) >= 3:
                self.rivers.append((path[0], path[-1]))
                for i in range(len(path) - 1):
                    self.rivers.append((path[i], path[i + 1]))

    def _generate_landmarks(self):
        """Place ancient ruins/landmarks."""
        candidates = [(q, r) for (q, r), t in self.tiles.items()
                       if t.terrain_type == TerrainType.PLAINS or t.terrain_type == TerrainType.GRASSLAND]
        names = ["Ancient Ruins", "Burial Mound", "Crystal Springs", "Monolith", "Old Fortress"]
        for _ in range(min(3, len(candidates))):
            if not candidates:
                break
            pos = random.choice(candidates)
            if pos not in self.landmarks:
                self.landmarks[pos] = random.choice(names)
                candidates.remove(pos)


def render_map(improved_map: ImprovedMap, fog: ImprovedFogOfWar, cities=None, units=None,
               show_territory: bool = False, show_resources: bool = True) -> str:
    """Render the map as ASCII art."""
    if not improved_map.tiles:
        return "Map is empty.\n"

    q_coords = [t.q for t in improved_map.tiles.values()]
    r_coords = [t.r for t in improved_map.tiles.values()]
    min_q, max_q = min(q_coords), max(q_coords)
    min_r, max_r = min(r_coords), max(r_coords)

    city_set = {(c.center_tile) for c in cities} if cities else set()
    unit_set = {(u.position) for u in units} if units else set()

    # Resource display icons
    resource_icons = {
        ResourceType.BONUS_WHEAT: "🌾",
        ResourceType.BONUS_FISH: "🐟",
        ResourceType.BONUS_GAME: "🦌",
        ResourceType.LUXURY_SILK: "🧣",
        ResourceType.LUXURY_SPICES: "🌶",
        ResourceType.LUXURY_IVORY: "🦴",
        ResourceType.STRATEGIC_IRON: "⚙",
        ResourceType.STRATEGIC_HORSES: "🐴",
        ResourceType.STRATEGIC_OIL: "🛢",
    }

    lines = []
    lines.append(f"\n{'='*(max_q-min_q+6)}")

    for r in range(max_r, min_r - 1, -1):
        indent = " " * (abs(r) % 2)
        row = indent
        for q in range(min_q, max_q + 1):
            tile = improved_map.get_tile(q, r)
            if not tile:
                row += "   "
                continue

            key = (q, r)
            is_visible = fog.is_visible(*key)
            is_discovered = key in fog.discovered

            if not is_discovered:
                row += " ??? "
            elif key in city_set:
                row += " [C] "
            elif key in unit_set:
                row += " [U] "
            elif key in improved_map.landmarks:
                row += f" [{improved_map.landmarks[key][0]}] "
            elif show_resources and key in improved_map.resources:
                res = improved_map.resources[key]
                icon = resource_icons.get(res, "?")
                row += f" [{icon}] "
            elif tile.terrain == TerrainType.MOUNTAIN:
                row += " [M] "
            elif tile.terrain == TerrainType.FOREST:
                row += " [F] "
            elif tile.terrain == TerrainType.PLAINS or tile.terrain == TerrainType.GRASSLAND:
                row += " [.] "
            elif tile.terrain == TerrainType.DESERT:
                row += " [:] "
            elif tile.terrain == TerrainType.TUNDRA:
                row += " [~] "
            elif tile.terrain == TerrainType.WATER_COAST:
                row += " [-] "
            elif tile.terrain == TerrainType.OCEAN:
                row += " [~] "
            elif tile.terrain == TerrainType.HILLS:
                row += " [v] "
            else:
                row += " [?] "
        lines.append(row)

    lines.append(f"{'='*(max_q-min_q+6)}")
    resource_legend = " ".join(f"{icon}={name.display_name}" for name, icon in resource_icons.items())
    lines.append(f"Legend: [C]City [U]Unit [M]Mountain [F]Forest [.]Plains [:]Desert [v]Hills [-]Coast [~]Ocean [?]Hidden  Resources: {resource_legend}\n")
    return "\n".join(lines)


def render_map(hexamap, fog_dict=None, cities=None, units=None):
    """Render a HexMap as ASCII art. fog_dict is { (x,y): bool } for discovered tiles."""
    if not hexamap.tiles:
        return "Map is empty.\n"
    terrain_chars = {
        TerrainType.PLAINS: ".", TerrainType.GRASSLAND: ".",
        TerrainType.FOREST: "F", TerrainType.HILLS: "^",
        TerrainType.MOUNTAIN: "#", TerrainType.DESERT: ":",
        TerrainType.TUNDRA: "~", TerrainType.WATER_COAST: "-",
        TerrainType.OCEAN: "~",
    }
    city_set = {c.position for c in cities} if cities else set()
    unit_set = {u.position for u in units} if units else set()
    q_coords = [t.x for t in hexamap.tiles.values()]
    r_coords = [t.y for t in hexamap.tiles.values()]
    min_q, max_q = min(q_coords), max(q_coords)
    min_r, max_r = min(r_coords), max(r_coords)
    lines = []
    lines.append(f"\n{'='*(max_q-min_q+6)}")
    for r in range(max_r, min_r - 1, -1):
        indent = " " * (abs(r) % 2)
        row = indent
        for q in range(min_q, max_q + 1):
            key = (q, r)
            tile = hexamap.get_tile(q, r)
            if not tile:
                row += "   "
                continue
            is_discovered = fog_dict.get(key, False) if fog_dict else False
            if not is_discovered:
                row += " ??? "
            elif key in city_set:
                row += " [C] "
            elif key in unit_set:
                row += " [U] "
            elif tile.resource is not None:
                row += " [R] "
            elif tile.terrain == TerrainType.MOUNTAIN:
                row += " [M] "
            elif tile.terrain == TerrainType.FOREST:
                row += " [F] "
            elif tile.terrain in (TerrainType.PLAINS, TerrainType.GRASSLAND):
                row += " [.] "
            elif tile.terrain == TerrainType.HILLS:
                row += " [v] "
            elif tile.terrain == TerrainType.DESERT:
                row += " [:] "
            elif tile.terrain == TerrainType.TUNDRA:
                row += " [~] "
            elif tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
                row += " [-] "
            else:
                row += " [?] "
        lines.append(row)
    lines.append(f"{'='*(max_q-min_q+6)}")
    lines.append("Legend: [C]City [U]Unit [M]Mountain [F]Forest [.]Plains [:]Desert [v]Hills [-]Coast [~]Ocean [?]Hidden\n")
    return "\n".join(lines)
