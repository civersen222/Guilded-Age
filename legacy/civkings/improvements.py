"""
CivKings - Tile Improvement System
Manages Worker units building tile improvements (farms, mines, etc.)
"""
from typing import Dict, List, Optional, Tuple, Set
from hex_map import HexTile


# Improvement definitions: name -> config
IMPROVEMENTS: Dict[str, Dict] = {
    'Farm': {
        'terrain': ['PLAINS', 'GRASSLAND'],
        'yields': {'food': 1},
        'build_turns': 3,
    },
    'Mine': {
        'terrain': ['HILLS', 'MOUNTAIN'],
        'yields': {'production': 1},
        'build_turns': 3,
    },
    'Lumber Mill': {
        'terrain': ['FOREST'],
        'yields': {'production': 1},
        'build_turns': 3,
    },
    'Trading Post': {
        'terrain': 'any',
        'yields': {'gold': 1},
        'build_turns': 3,
    },
    'Pasture': {
        'terrain': ['PLAINS', 'GRASSLAND'],
        'yields': {'production': 1},
        'build_turns': 3,
    },
}


class ImprovementManager:
    """Manages tile improvements built by Worker units."""

    def __init__(self):
        self._active_improvements: Dict[Tuple[int, int], str] = {}
        # Map (x,y) -> improvement_type currently being built

    def can_improve(self, tile: HexTile, improvement_type: str) -> bool:
        """Check if a tile can receive this improvement."""
        if tile.improvement is not None:
            return False
        if tile.city:
            return False

        imp = IMPROVEMENTS.get(improvement_type)
        if not imp:
            return False

        allowed_terrains = imp['terrain']
        if allowed_terrain == 'any':
            return True
        return tile.terrain.name in allowed_terrains

    def start_improvement(self, tile: HexTile, improvement_type: str) -> bool:
        """Start building an improvement on a tile. Returns True if successful."""
        if not self.can_improve(tile, improvement_type):
            return False

        imp = IMPROVEMENTS[improvement_type]
        tile.improvement = improvement_type
        tile.improvement_progress = 0
        self._active_improvements[(tile.x, tile.y)] = improvement_type
        print(f"  🏗️ Started building {improvement_type} on ({tile.x},{tile.y})")
        return True

    def process_turn(self, tiles_with_workers: Set[Tuple[int, int]], all_tiles: Dict[Tuple[int, int], HexTile]) -> List[str]:
        """Advance all active improvements. Returns progress messages."""
        msgs = []
        completed = []

        for (x, y), imp_type in list(self._active_improvements.items()):
            if (x, y) not in tiles_with_workers:
                continue

            tile = all_tiles.get((x, y))
            if not tile:
                continue

            imp = IMPROVEMENTS.get(imp_type)
            if not imp:
                continue

            tile.improvement_progress += 1
            if tile.improvement_progress >= imp['build_turns']:
                tile.improvement_progress = -1  # -1 = complete
                completed.append((x, y, imp_type))
                msgs.append(f"  ✅ {imp_type} completed on ({x},{y})")
                print(f"  ✅ {imp_type} completed on ({x},{y})")

        for x, y, imp_type in completed:
            del self._active_improvements[(x, y)]

        return msgs

    def get_available_improvements(self, tile: HexTile) -> List[str]:
        """Return list of valid improvement types for this tile."""
        available = []
        for imp_name, imp_config in IMPROVEMENTS.items():
            if self.can_improve(tile, imp_name):
                available.append(imp_name)
        return available
