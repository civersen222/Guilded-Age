"""Main gameplay screen — coordinates map, panels, popups, minimap, and interaction."""
import pygame
import pygame_gui

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    MAP_X, MAP_Y, MAP_W, MAP_H,
    RESOURCE_BAR_HEIGHT, ACTION_BAR_HEIGHT,
    LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
    PANEL_BG, BORDER, BG, TEXT, GOLD,
)
from pygame_app.map.camera import Camera
from pygame_app.map.tile_atlas import TileAtlas
from pygame_app.map.hex_renderer import HexRenderer
from pygame_app.map.minimap import Minimap


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, minimap, and manages interaction."""

    def __init__(self, app):
        super().__init__(app)
        self._camera = None
        self._atlas = None
        self._hex_renderer = None
        self._minimap = None
        self._map_surface = None
        self._resource_label = None
        self._next_turn_btn = None
        self._panning = False
        self._pan_start = (0, 0)
        self._dragging_middle = False
        self._drag_start = (0, 0)
        self._held_keys = set()

    def enter(self):
        game = self.app.game
        screen_w = SCREEN_WIDTH
        screen_h = SCREEN_HEIGHT

        # Camera
        self._camera = Camera(MAP_W, MAP_H)

        # Tile atlas
        self._atlas = TileAtlas("assets/tiles")

        # Hex renderer
        self._hex_renderer = HexRenderer(game.map, self._atlas, self._camera)

        # Minimap
        self._minimap = Minimap(game.map, self._camera)

        # Center camera on first city (capital)
        cities = list(game.cities.values())
        if cities:
            first_city = cities[0]
            pos = getattr(first_city, "position", (0, 0))
            wx, wy = HexRenderer.hex_to_world(pos[0], pos[1])
            self._camera.snap_to(wx, wy)

        # Map surface
        self._map_surface = pygame.Surface((MAP_W, MAP_H))

        # Resource bar label
        self._resource_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(MAP_X + 5, MAP_Y + 5, MAP_W - 10, RESOURCE_BAR_HEIGHT - 10),
            text=self._format_resource_text(game),
            manager=self.ui_manager,
        )

        # Next Turn button
        self._next_turn_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH - 20,
                                      SCREEN_HEIGHT - ACTION_BAR_HEIGHT - 15,
                                      140, 35),
            text="Next Turn",
            manager=self.ui_manager,
        )

    def exit(self):
        if self._resource_label:
            self._resource_label.kill()
        if self._next_turn_btn:
            self._next_turn_btn.kill()

    def _format_resource_text(self, game):
        """Format the resource bar text."""
        civ_name = game.player_civ.name if hasattr(game.player_civ, "name") else "Player"
        yields = game.city_manager.get_total_yields(civ_name, game.map.tiles)
        gold = game.gold.get(civ_name, 0)
        turn = game.state.turn
        f = yields.get("food", 0)
        p = yields.get("production", 0)
        g = gold
        s = yields.get("science", 0)
        return (
            f"{civ_name} | "
            f"Food: {f:.1f} | Prod: {p:.1f} | "
            f"Gold: {int(g)} | Sci: {s:.1f} | "
            f"Turn {turn}"
        )

    def handle_event(self, event):
        game = self.app.game

        # Next Turn button
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and hasattr(self, "_next_turn_btn")
                and event.ui_element == self._next_turn_btn):
            game.process_turn()
            self._resource_label.set_text(self._format_resource_text(game))
            return

        # Enter key = Next Turn
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            game.process_turn()
            self._resource_label.set_text(self._format_resource_text(game))
            return

        # Middle mouse button drag for panning
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self._dragging_middle = True
            self._drag_start = (event.pos[0], event.pos[1])
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self._dragging_middle = False
            return

        # Left click in map area: convert to hex
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Check map area
            if MAP_X <= mx <= MAP_X + MAP_W and MAP_Y <= my <= MAP_Y + MAP_H:
                sx = mx - MAP_X
                sy = my - MAP_Y
                hx, hy = self._hex_renderer.screen_to_hex(sx, sy)
                self._hex_renderer.selected_hex = (hx, hy)
                # Check minimap click
                if self._minimap:
                    self._minimap.handle_click(mx, my, SCREEN_HEIGHT)
                return

            # Check minimap click
            if self._minimap and self._minimap.handle_click(mx, my, SCREEN_HEIGHT):
                return

        # Mouse wheel zoom
        if event.type == pygame.MOUSEWHEEL:
            if event.y != 0:
                mx, my = event.pos
                factor = 1.1 if event.y > 0 else 0.9
                self._camera.zoom_at(mx, my, factor)
                return

        # Home key: center on first city
        if event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
            cities = list(game.cities.values())
            if cities:
                pos = getattr(cities[0], "position", (0, 0))
                wx, wy = HexRenderer.hex_to_world(pos[0], pos[1])
                self._camera.center_on(wx, wy)
            return

    def update(self, dt):
        # WASD / arrow key panning
        speed = 400 * dt / self._camera.zoom
        keys = pygame.key.get_pressed()
        dx, dy = 0.0, 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += speed
        if dx != 0 or dy != 0:
            self._camera.pan(dx, dy)

        # Middle mouse drag panning
        if self._dragging_middle:
            mx, my = pygame.mouse.get_pos()
            dx = mx - self._drag_start[0]
            dy = my - self._drag_start[1]
            self._camera.pan(dx, dy)
            self._drag_start = (mx, my)

        self._camera.update(dt)

    def draw(self, surface):
        # Fill map surface
        self._map_surface.fill(BG)
        if self._hex_renderer:
            self._hex_renderer.render(self._map_surface, self.app.game)
        surface.blit(self._map_surface, (MAP_X, MAP_Y))

        # Panel backgrounds
        # Top resource bar
        pygame.draw.rect(surface, PANEL_BG,
                         pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))
        # Bottom action bar
        pygame.draw.rect(surface, PANEL_BG,
                         pygame.Rect(0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT,
                                    SCREEN_WIDTH, ACTION_BAR_HEIGHT))
        # Left panel
        pygame.draw.rect(surface, PANEL_BG,
                         pygame.Rect(0, RESOURCE_BAR_HEIGHT,
                                    LEFT_PANEL_WIDTH,
                                    SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        # Right panel
        pygame.draw.rect(surface, PANEL_BG,
                         pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT,
                                    RIGHT_PANEL_WIDTH,
                                    SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))

        # Border lines
        # Top bar bottom border
        pygame.draw.line(surface, BORDER, (0, RESOURCE_BAR_HEIGHT),
                         (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))
        # Bottom bar top border
        bar_y = SCREEN_HEIGHT - ACTION_BAR_HEIGHT
        pygame.draw.line(surface, BORDER, (0, bar_y),
                         (SCREEN_WIDTH, bar_y))
        # Left panel right border
        pygame.draw.line(surface, BORDER,
                         (LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT),
                         (LEFT_PANEL_WIDTH, SCREEN_HEIGHT - ACTION_BAR_HEIGHT))
        # Right panel left border
        rx = SCREEN_WIDTH - RIGHT_PANEL_WIDTH
        pygame.draw.line(surface, BORDER,
                         (rx, RESOURCE_BAR_HEIGHT),
                         (rx, SCREEN_HEIGHT - ACTION_BAR_HEIGHT))
        # Map area borders
        pygame.draw.line(surface, BORDER, (MAP_X, MAP_Y), (MAP_X + MAP_W, MAP_Y))
        pygame.draw.line(surface, BORDER, (MAP_X, MAP_Y + MAP_H),
                         (MAP_X + MAP_W, MAP_Y + MAP_H))
        pygame.draw.line(surface, BORDER, (MAP_X, MAP_Y),
                         (MAP_X, MAP_Y + MAP_H))
        pygame.draw.line(surface, BORDER, (MAP_X + MAP_W, MAP_Y),
                         (MAP_X + MAP_W, MAP_Y + MAP_H))

        # Minimap
        if self._minimap:
            self._minimap.render(surface, self.app.game, SCREEN_HEIGHT)
