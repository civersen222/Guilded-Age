"""Load hex tile sprite atlases and provide terrain surfaces by type and zoom."""
import os
import json
import pygame


class TileAtlas:
    """Loads sprite sheet atlases and extracts terrain tile surfaces."""

    ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]
    # Map zoom float -> atlas filename suffix (z064, z096, z128, z192, z256)
    ZOOM_TO_SUFFIX = {0.5: "064", 0.75: "096", 1.0: "128", 1.5: "192", 2.0: "256"}
    # Map zoom float -> pixel size used in JSON keys (PLAINS_64, PLAINS_128, etc.)
    ZOOM_TO_SIZE = {0.5: 64, 0.75: 96, 1.0: 128, 1.5: 192, 2.0: 256}

    def __init__(self, tiles_dir: str):
        self.tiles_dir = tiles_dir
        self.atlases = {}       # {zoom_tag: pygame.Surface}
        self.tile_rects = {}    # {zoom_tag: {name: pygame.Rect}}
        self._tile_cache = {}   # {(terrain_name, zoom_tag): pygame.Surface}
        self._load_all()

    def _zoom_tag(self, zoom: float) -> str:
        return f"z{self.ZOOM_TO_SUFFIX[zoom]}"

    def _load_all(self):
        # Try new location first: assets/tiles/atlases/
        new_dir = os.path.join(self.tiles_dir, "atlases")
        old_dir = self.tiles_dir

        dirs_to_try = [new_dir] if os.path.isdir(new_dir) else []
        if os.path.isdir(old_dir):
            dirs_to_try.append(old_dir)

        for directory in dirs_to_try:
            for zoom in self.ZOOM_LEVELS:
                suffix = self.ZOOM_TO_SUFFIX[zoom]
                tag = f"z{suffix}"
                atlas_path = os.path.join(directory, f"atlas_{tag}.png")
                json_path = os.path.join(directory, f"atlas_{tag}.json")

                if not os.path.exists(atlas_path):
                    continue

                surface = pygame.image.load(atlas_path).convert_alpha()
                self.atlases[tag] = surface

                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        rects = json.load(f)
                    # JSON keys are like "PLAINS_128" — keep them as-is
                    self.tile_rects[tag] = {
                        name: pygame.Rect(r['x'], r['y'], r['w'], r['h'])
                        for name, r in rects.items()
                    }

    def _nearest_zoom(self, zoom: float) -> str:
        nearest = min(self.ZOOM_LEVELS, key=lambda z: abs(z - zoom))
        return self._zoom_tag(nearest)

    def get_tile(self, terrain_name: str, zoom: float = 1.0) -> pygame.Surface:
        """Get the tile surface for a terrain type at the nearest zoom level.

        Args:
            terrain_name: Terrain enum name (e.g. 'PLAINS', 'OCEAN').
            zoom: Current camera zoom level.

        Returns:
            pygame.Surface with the hex tile image (with alpha).
        """
        tag = self._nearest_zoom(zoom)
        nearest = min(self.ZOOM_LEVELS, key=lambda z: abs(z - zoom))
        size = self.ZOOM_TO_SIZE[nearest]
        key = f"{terrain_name}_{size}"
        cache_key = (key, tag)

        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        if tag not in self.atlases or key not in self.tile_rects.get(tag, {}):
            # Return a small red square as error indicator
            s = pygame.Surface((32, 32), pygame.SRCALPHA)
            s.fill((255, 0, 0, 128))
            return s

        rect = self.tile_rects[tag][key]
        tile_surface = self.atlases[tag].subsurface(rect).copy()
        self._tile_cache[cache_key] = tile_surface
        return tile_surface

    @property
    def loaded(self) -> bool:
        return len(self.atlases) > 0
