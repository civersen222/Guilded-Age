"""Camera system — pan, zoom, viewport culling, coordinate transforms."""
import math
from typing import Tuple


class Camera:
    """Manages the viewport into the hex world."""

    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Current state
        self.x = 0.0           # World center X
        self.y = 0.0           # World center Y
        self.zoom = 1.0

        # Target state (for smooth lerp)
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_zoom = 1.0

        # Limits
        self.min_zoom = 0.3
        self.max_zoom = 3.0
        self.lerp_speed = 10.0

        # Mouse drag state
        self._dragging = False
        self._drag_start = (0, 0)

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world coordinates to screen pixel position."""
        sx = (wx - self.x) * self.zoom + self.screen_w / 2
        sy = (wy - self.y) * self.zoom + self.screen_h / 2
        return int(sx), int(sy)

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        """Convert screen pixel to world coordinates."""
        wx = (sx - self.screen_w / 2) / self.zoom + self.x
        wy = (sy - self.screen_h / 2) / self.zoom + self.y
        return wx, wy

    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        """Return (min_wx, min_wy, max_wx, max_wy) of visible world area."""
        half_w = (self.screen_w / 2) / self.zoom
        half_h = (self.screen_h / 2) / self.zoom
        return (
            self.x - half_w, self.y - half_h,
            self.x + half_w, self.y + half_h,
        )

    def update(self, dt: float):
        """Smooth lerp toward target position/zoom."""
        t = min(1.0, self.lerp_speed * dt)
        self.x += (self.target_x - self.x) * t
        self.y += (self.target_y - self.y) * t
        self.zoom += (self.target_zoom - self.zoom) * t

    def pan(self, dx: float, dy: float):
        """Pan the camera by screen-space delta."""
        self.target_x += dx / self.zoom
        self.target_y += dy / self.zoom

    def zoom_at(self, screen_x: int, screen_y: int, factor: float):
        """Zoom centered on a screen position."""
        # Get world point under cursor before zoom
        wx, wy = self.screen_to_world(screen_x, screen_y)

        new_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom * factor))
        self.target_zoom = new_zoom

        # Adjust target position so the world point stays under cursor
        self.target_x = wx - (screen_x - self.screen_w / 2) / new_zoom
        self.target_y = wy - (screen_y - self.screen_h / 2) / new_zoom

    def center_on(self, wx: float, wy: float):
        """Smoothly center camera on a world position."""
        self.target_x = wx
        self.target_y = wy

    def snap_to(self, wx: float, wy: float):
        """Immediately center camera (no lerp)."""
        self.x = self.target_x = wx
        self.y = self.target_y = wy

    def resize(self, new_w: int, new_h: int):
        """Handle window resize."""
        self.screen_w = new_w
        self.screen_h = new_h
