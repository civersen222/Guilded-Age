"""Load hex tile sprite atlases and provide terrain surfaces by type and zoom."""
import os
import json
import pygame


class TileAtlas:
    """Loads sprite sheet atlases and extracts terrain tile surfaces."""

    ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]

    def __init__(self, tiles_dir: str):
        self.tiles_dir = tiles_dir
        self.atlases = {}       # {zoom_tag: pygame.Surface}
        self.tile_rects = {}    # {zoom_tag: {name: pygame.Rect}}
        self._tile_cache = {}   # {(terrain_name, zoom_tag): pygame.Surface}
        self._load_all()

    def _zoom_tag(self, zoom: float) -> str:
        return f"z{zoom:.1f}".replace('.', '_')

    def _load_all(self):
        for zoom in self.ZOOM_LEVELS:
            tag = self._zoom_tag(zoom)
            atlas_path = os.path.join(self.tiles_dir, f"atlas_{tag}.png")
            json_path = os.path.join(self.tiles_dir, f"atlas_{tag}.json")

            if not os.path.exists(atlas_path):
                continue

            surface = pygame.image.load(atlas_path).convert_alpha()
            self.atlases[tag] = surface

            with open(json_path, 'r') as f:
                rects = json.load(f)
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
        key = f"{terrain_name}_0"
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
