"""Minimap — small overview map in the bottom-left corner."""

import pygame


class Minimap:
    """Renders a 200x200 minimap of the hex world."""

    SIZE = 200
    MARGIN = 10

    def __init__(self, hex_map, camera):
        self.hex_map = hex_map
        self.camera = camera
        self._base_surface = None
        self._world_bounds = None  # (min_x, max_x, min_y, max_y)
        self._scale = None
        self._render_base()

    def _render_base(self):
        """Pre-render terrain as colored dots onto a cached surface."""
        self._base_surface = pygame.Surface((self.SIZE, self.SIZE), pygame.SRCALPHA)
        tiles = self.hex_map.tiles
        if not tiles:
            return

        # Determine world bounds
        xs = [t.x for t in tiles.values()]
        ys = [t.y for t in tiles.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        self._world_bounds = (min_x, max_x, min_y, max_y)

        # Scale factors
        world_w = max_x - min_x + 1
        world_h = max_y - min_y + 1
        scale_x = self.SIZE / world_w
        scale_y = self.SIZE / world_h
        self._scale = min(scale_x, scale_y)

        from pygame_app.constants import TERRAIN_COLORS

        for tile in tiles.values():
            sx = self.MARGIN + (tile.x - min_x) * self._scale
            sy = self.SIZE - self.MARGIN - (tile.y - min_y) * self._scale
            color = TERRAIN_COLORS.get(tile.terrain.name, (100, 100, 100))
            pygame.draw.rect(self._base_surface, color, (int(sx), int(sy), 2, 2))

    def render(self, surface, game, screen_h):
        """Blit minimap onto the main surface."""
        if self._base_surface is None or self._world_bounds is None:
            return

        x = self.MARGIN
        y = screen_h - self.SIZE - self.MARGIN

        # Draw base terrain
        surface.blit(self._base_surface, (x, y))

        # Draw city dots
        cities = getattr(game, "cities", {})
        player_name = game.player_civ.name if hasattr(game.player_civ, "name") else ""
        min_x, max_x, min_y, max_y = self._world_bounds

        for city_id, city in cities.items():
            pos = getattr(city, "position", (0, 0))
            cx, cy = pos
            dot_x = x + (cx - min_x) * self._scale
            dot_y = y + self.SIZE - self.MARGIN - (cy - min_y) * self._scale - self.SIZE
            is_player = getattr(city, "owner", "") == player_name
            colour = (255, 215, 0) if is_player else (178, 58, 58)
            pygame.draw.circle(surface, colour, (int(dot_x), int(dot_y)), 3)

        # Draw viewport rectangle
        bounds = self.camera.get_visible_bounds()
        vx = x + (bounds[0] - min_x) * self._scale
        vy = y + self.SIZE - self.MARGIN - (bounds[3] - min_y) * self._scale - self.SIZE
        vw = (bounds[2] - bounds[0]) * self._scale
        vh = (bounds[3] - bounds[1]) * self._scale
        pygame.draw.rect(surface, (255, 255, 255), (int(vx), int(vy), int(vw), int(vh)), 1)

    def handle_click(self, mx, my, screen_h):
        """If click is in minimap area, convert to world coords and center camera. Returns True if handled."""
        x = self.MARGIN
        y = screen_h - self.SIZE - self.MARGIN
        if not (x <= mx <= x + self.SIZE and y <= my <= y + self.SIZE):
            return False

        # Convert click offset within minimap to world coords
        offset_x = mx - x
        offset_y = my - y

        if self._world_bounds is None:
            return False

        min_x, max_x, min_y, max_y = self._world_bounds
        world_w = max_x - min_x + 1
        world_h = max_y - min_y + 1
        scale_x = self.SIZE / world_w
        scale_y = self.SIZE / world_h
        scale = min(scale_x, scale_y)

        # Map click position back to world coordinates
        world_x = min_x + offset_x / scale
        world_y = min_y + (self.SIZE - self.MARGIN - offset_y) / scale

        self.camera.center_on(world_x, world_y)
        return True
