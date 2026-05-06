"""Main gameplay screen — coordinates map, panels, popups, minimap, and interaction."""
import pygame
import pygame_gui

from pygame_app.screens.base import BaseScreen
from game_data import TerrainType

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
from pygame_app.panels.resource_bar import ResourceBar
from pygame_app.panels.city_panel import CityPanel
from pygame_app.panels.unit_panel import UnitPanel
from pygame_app.panels.event_log import EventLog
from pygame_app.panels.turn_summary import TurnSummary
from pygame_app.panels.action_bar import ActionBar


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, minimap, and manages interaction."""

    def __init__(self, app):
        super().__init__(app)
        self._camera = None
        self._atlas = None
        self._hex_renderer = None
        self._minimap = None
        self._map_surface = None
        self._resource_bar = None
        self._city_panel = None
        self._event_log = None
        self._turn_summary = None
        self._action_bar = None
        self._next_turn_btn = None
        self._unit_panel = None
        self._selected_unit = None
        self._selected_city = None
        self._panning = False
        self._pan_start = (0, 0)
        self._dragging_middle = False
        self._drag_start = (0, 0)
        self._held_keys = set()
        self._active_popup = None
        self.show_yields = False
        self._elapsed = 0.0

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

        # Resource bar
        self._resource_bar = ResourceBar(self.ui_manager, game)

        # City panel (left sidebar)
        self._city_panel = CityPanel(
            self.ui_manager,
            pygame.Rect(0, RESOURCE_BAR_HEIGHT, LEFT_PANEL_WIDTH, 400),
        )
        self._city_panel.refresh(game)

        # Event log (right sidebar)
        self._event_log = EventLog(
            self.ui_manager,
            pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT,
                        RIGHT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT),
        )

        # Action bar (bottom bar)
        self._action_bar = ActionBar(self.ui_manager)
        self._action_bar.set_mode("default")

        # Unit panel (below city panel)
        self._unit_panel = UnitPanel(
            self.ui_manager,
            pygame.Rect(0, RESOURCE_BAR_HEIGHT + 400, LEFT_PANEL_WIDTH, 300),
        )
        self._unit_panel.refresh(game)

        # Turn summary (modal popup)
        self._turn_summary = TurnSummary()

        # Next Turn button
        self._next_turn_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH - 20,
                                      SCREEN_HEIGHT - ACTION_BAR_HEIGHT - 15,
                                      140, 35),
            text="Next Turn",
            manager=self.ui_manager,
        )

    def exit(self):
        if self._resource_bar:
            self._resource_bar.destroy()
        if self._city_panel:
            self._city_panel.destroy()
        if self._event_log:
            self._event_log.destroy()
        if self._action_bar:
            self._action_bar.destroy()
        if self._unit_panel:
            self._unit_panel.destroy()
        if self._turn_summary and self._turn_summary.is_visible:
            self._turn_summary._kill()
        if self._next_turn_btn:
            self._next_turn_btn.kill()



    def handle_event(self, event):
        game = self.app.game

        # Mouse wheel zoom MUST come before any event.pos access
        if event.type == pygame.MOUSEWHEEL:
            if event.y != 0:
                mx, my = pygame.mouse.get_pos()
                factor = 1.15 if event.y > 0 else 1 / 1.15
                local_x = mx - MAP_X
                local_y = my - MAP_Y
                self._camera.zoom_at(local_x, local_y, factor)
                return

        # Turn summary dismiss
        if self._turn_summary and self._turn_summary.is_visible:
            if self._turn_summary.handle_event(event):
                return

        # Action bar buttons
        action = self._action_bar.handle_event(event)
        if action is not None:
            self._handle_action(action, game)
            return

        # Production popup events
        if hasattr(self, "_production_popup") and self._production_popup is not None:
            if self._production_popup.handle_event(event):
                return

        # Next Turn button
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and hasattr(self, "_next_turn_btn")
                and event.ui_element == self._next_turn_btn):
            game.process_turn()
            if game.tech_manager.current_research is None:
                available = game.tech_manager.get_available_techs()
                if available:
                    tech = available[0]
                    tech_name = tech.name if hasattr(tech, 'name') else str(tech)
                    game.tech_manager.start_research(tech)
                    self._event_log.add_event(f"Auto-researching: {tech_name}", "science")
            self._resource_bar.refresh(game)
            self._city_panel.refresh(game)
            events = game.state.turn_events or []
            for evt_text in events:
                self._event_log.add_event(str(evt_text), "info")
            return

        # Enter key = Next Turn
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            game.process_turn()
            if game.tech_manager.current_research is None:
                available = game.tech_manager.get_available_techs()
                if available:
                    tech = available[0]
                    tech_name = tech.name if hasattr(tech, 'name') else str(tech)
                    game.tech_manager.start_research(tech)
                    self._event_log.add_event(f"Auto-researching: {tech_name}", "science")
            self._resource_bar.refresh(game)
            self._city_panel.refresh(game)
            events = game.state.turn_events or []
            for evt_text in events:
                self._event_log.add_event(str(evt_text), "info")
            return

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        if event.type == pygame.KEYDOWN:

            # Escape: close popup or deselect
            if event.key == pygame.K_ESCAPE:
                if self._active_popup:
                    self._active_popup._kill()
                    self._active_popup = None
                elif self._selected_unit:
                    self._selected_unit = None
                    self._action_bar.set_mode("default")
                    self._hex_renderer.move_range.clear()
                    self._hex_renderer.attack_range.clear()
                return

            # Space: skip selected unit turn
            if event.key == pygame.K_SPACE and self._selected_unit:
                self._selected_unit.moves_left = 0
                self._hex_renderer.move_range.clear()
                self._unit_panel.refresh(game)
                self._event_log.add_event(f"{self._selected_unit.unit_type} skipped", "info")
                return

            # Tab: cycle to next unit with moves remaining
            if event.key == pygame.K_TAB:
                player_name = game.player_civ.name
                units = [
                    u for u in game.units.values()
                    if getattr(u, "is_alive", False)
                    and getattr(u, "owner", "") == player_name
                    and getattr(u, "moves_left", 0) > 0
                ]
                if units and self._selected_unit:
                    try:
                        idx = units.index(self._selected_unit)
                        self._select_unit(game, units[(idx + 1) % len(units)])
                    except ValueError:
                        self._select_unit(game, units[0])
                elif units:
                    self._select_unit(game, units[0])
                return

            # T: open tech tree
            if event.key == pygame.K_t:
                if self._active_popup:
                    self._active_popup._kill()
                    self._active_popup = None
                from pygame_app.popups.tech_tree import TechTreePopup
                popup = TechTreePopup()
                popup.show(self.ui_manager, game)
                self._active_popup = popup
                return

            # D: open diplomacy
            if event.key == pygame.K_d:
                if self._active_popup:
                    self._active_popup._kill()
                    self._active_popup = None
                from pygame_app.popups.diplomacy import DiplomacyPopup
                popup = DiplomacyPopup()
                popup.show(self.ui_manager, game)
                self._active_popup = popup
                return

            # Y: open dynasty
            if event.key == pygame.K_y:
                if self._active_popup:
                    self._active_popup._kill()
                    self._active_popup = None
                from pygame_app.popups.dynasty import DynastyPopup
                popup = DynastyPopup()
                popup.show(self.ui_manager, game)
                self._active_popup = popup
                return

            # P: open production popup for selected city
            if event.key == pygame.K_p:
                if self._active_popup:
                    self._active_popup._kill()
                    self._active_popup = None
                from pygame_app.popups.production import ProductionPopup
                popup = ProductionPopup()
                popup.show(self.ui_manager, None, game)
                self._active_popup = popup
                return

            # F: fortify selected unit
            if event.key == pygame.K_f and self._selected_unit:
                self._selected_unit.is_fortified = True
                self._event_log.add_event(f"{self._selected_unit.unit_type} fortified", "info")
                return

            # +/= : zoom in
            if event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                if not hasattr(event, "pos"):
                    return
                mx, my = event.pos
                self._camera.zoom_at(mx - MAP_X, my - MAP_Y, 1.15)
                return

            # -: zoom out
            if event.key == pygame.K_MINUS:
                if not hasattr(event, "pos"):
                    return
                mx, my = event.pos
                self._camera.zoom_at(mx - MAP_X, my - MAP_Y, 1 / 1.15)
                return

            # G: toggle yield overlay
            if event.key == pygame.K_g:
                self.show_yields = not self.show_yields
                self._event_log.add_event(
                    "Yield overlay ON" if self.show_yields else "Yield overlay OFF", "info"
                )
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
                hx, hy = self._hex_renderer.screen_to_hex(mx - MAP_X, my - MAP_Y)
                self._hex_renderer.selected_hex = (hx, hy)
                self._hex_renderer.move_range.clear()
                self._hex_renderer.attack_range.clear()
                # Check for a player unit at this hex and select it
                self._select_unit_at_hex(game, hx, hy)
                # Check for a player city at this hex and open production popup
                player_name = getattr(game.player_civ, "name", "")
                for city in game.cities.values():
                    if getattr(city, "owner", "") == player_name and getattr(city, "position", None) == (hx, hy):
                        self._selected_city = city
                        self._open_production_popup(game, city)
                        return
 
                # Check minimap click
                if self._minimap:
                    self._minimap.handle_click(mx, my, SCREEN_HEIGHT)
                return

            # Check minimap click
            if self._minimap and self._minimap.handle_click(mx, my, SCREEN_HEIGHT):
                return

        # Unit panel button click: select unit
        unit = self._unit_panel.handle_event(event)
        if unit is not None:
            self._select_unit(game, unit)
            return

        # City panel button click: center camera on that city
        city = self._city_panel.handle_event(event)
        if city is not None:
            pos = getattr(city, "position", (0, 0))
            wx, wy = HexRenderer.hex_to_world(pos[0], pos[1])
            self._camera.center_on(wx, wy)
            return

        # Home key: center on first city
        if event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
            cities = list(game.cities.values())
            if cities:
                pos = getattr(cities[0], "position", (0, 0))
                wx, wy = HexRenderer.hex_to_world(pos[0], pos[1])
                self._camera.center_on(wx, wy)
            return

        # Right-click to move selected unit
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            mx, my = event.pos
            if MAP_X <= mx <= MAP_X + MAP_W and MAP_Y <= my <= MAP_Y + MAP_H:
                if self._selected_unit:
                    sx = mx - MAP_X
                    sy = my - MAP_Y
                    hx, hy = self._hex_renderer.screen_to_hex(sx, sy)
                    self._move_selected_unit(game, hx, hy)
            return

    def _handle_action(self, action: str, game) -> None:
        """Handle an action from the action bar."""
        if action == "Next Turn":
            game.process_turn()
            if game.tech_manager.current_research is None:
                available = game.tech_manager.get_available_techs()
                if available:
                    tech = available[0]
                    tech_name = tech.name if hasattr(tech, 'name') else str(tech)
                    game.tech_manager.start_research(tech)
                    self._event_log.add_event(f"Auto-researching: {tech_name}", "science")
            self._resource_bar.refresh(game)
            self._city_panel.refresh(game)
            self._unit_panel.refresh(game)
            self._event_log.add_event(f"Turn advanced to turn {game.state.turn}", "info")
            events = game.state.turn_events or []
            for evt_text in events:
                self._event_log.add_event(str(evt_text), "info")
        elif action == "Save":
            self._save_game(game)
        elif action in ("Move", "Attack", "Fortify", "Skip"):
            self._handle_unit_action(action, game)
        elif action == "Tech Tree":
            from pygame_app.popups.tech_tree import TechTreePopup
            popup = TechTreePopup()
            popup.show(self.ui_manager, game)
            self._tech_popup = popup
        elif action == "Diplomacy":
            from pygame_app.popups.diplomacy import DiplomacyPopup
            popup = DiplomacyPopup()
            popup.show(self.ui_manager, game)
            self._diplomacy_popup = popup
        elif action == "Dynasty":
            from pygame_app.popups.dynasty import DynastyPopup
            popup = DynastyPopup()
            popup.show(self.ui_manager, game)
            self._dynasty_popup = popup
        elif action == "Production":
            self._show_production(game, self._selected_city)
        elif action == "Settle":
            self._settle_city(game)

    def _save_game(self, game) -> None:
        """Save the current game state."""
        from save_system import save_game
        path = save_game(game)
        self._event_log.add_event(f"Game saved to {path}", "success")

    def _select_unit(self, game, unit) -> None:
        """Select a unit and show its move range."""
        self._selected_unit = unit
        player_name = game.player_civ.name
        if unit.owner != player_name:
            self._selected_unit = None
            return
        self._hex_renderer.selected_hex = getattr(unit, "position", (0, 0))
        self._hex_renderer.attack_range.clear()
        # Calculate move range
        moves_left = getattr(unit, "moves_left", 0)
        if moves_left > 0:
            game._player_name = player_name
            self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(
                getattr(unit, "position", (0, 0)), moves_left, game.units, game
            )
        # Check if this is a Settler to show Settle button
        if getattr(unit, "unit_type", "") == "Settler":
            self._action_bar.set_mode("settler_selected")
        else:
            self._action_bar.set_mode("unit_selected")

    def _select_unit_at_hex(self, game, hx, hy) -> None:
        """Select unit at hex if it belongs to player."""
        player_name = game.player_civ.name
        for uid, unit in game.units.items():
            if (getattr(unit, "is_alive", False)
                    and getattr(unit, "position", None) == (hx, hy)
                    and getattr(unit, "owner", "") == player_name):
                self._select_unit(game, unit)
                return
        self._selected_unit = None
        self._action_bar.set_mode("default")

    def _move_selected_unit(self, game, hx, hy) -> None:
        """Move selected unit to target hex."""
        if not self._selected_unit:
            return
        unit = self._selected_unit
        success = game.military_manager.move_unit(unit, (hx, hy))
        if success:
            self._event_log.add_event(f"{unit.unit_type} moved to ({hx},{hy})", "success")
            # Recalculate move range
            moves_left = getattr(unit, "moves_left", 0)
            if moves_left > 0:
                self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(
                    getattr(unit, "position", (0, 0)), moves_left, game.units, game
                )
            else:
                self._hex_renderer.move_range.clear()
            self._unit_panel.refresh(game)
        else:
            self._event_log.add_event(f"Cannot move {unit.unit_type} to ({hx},{hy})", "error")

    def _handle_unit_action(self, action: str, game) -> None:
        """Handle Move/Attack/Fortify/Skip actions."""
        if not self._selected_unit:
            return
        unit = self._selected_unit

        if action == "Move":
            # Show move range, wait for right-click
            moves_left = getattr(unit, "moves_left", 0)
            if moves_left > 0:
                game._player_name = game.player_civ.name
                self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(
                    getattr(unit, "position", (0, 0)), moves_left, game.units, game
                )
                self._event_log.add_event("Right-click to move", "info")
            else:
                self._event_log.add_event("Unit has no moves left", "error")

        elif action == "Attack":
            # Show attack range (enemy units adjacent)
            game._player_name = game.player_civ.name
            self._hex_renderer.attack_range = self._hex_renderer.calculate_attack_range(
                getattr(unit, "position", (0, 0)), game.units, game
            )
            if self._hex_renderer.attack_range:
                self._event_log.add_event("Select an enemy hex to attack", "info")
            else:
                self._event_log.add_event("No enemies in attack range", "error")

        elif action == "Fortify":
            unit.is_fortified = True
            self._event_log.add_event(f"{unit.unit_type} fortified", "info")

        elif action == "Skip":
            unit.moves_left = 0
            self._event_log.add_event(f"{unit.unit_type} skipped", "info")
            self._unit_panel.refresh(game)

    def _settle_city(self, game) -> None:
        """Settle a new city at the selected Settler's current position."""
        if not self._selected_unit:
            return
        unit = self._selected_unit
        if getattr(unit, "unit_type", "") != "Settler":
            return

        position = getattr(unit, "position", None)
        if position is None:
            return

        # Check no existing city at this position
        for city in game.cities.values():
            if getattr(city, "position", None) == position:
                self._event_log.add_event("A city already exists here", "error")
                return

        # Check no enemy unit at this position
        player_name = game.player_civ.name
        for uid, u in game.units.items():
            if getattr(u, "is_alive", False) and getattr(u, "owner", "") != player_name:
                if getattr(u, "position", None) == position:
                    self._event_log.add_event("Cannot settle on an enemy unit", "error")
                    return

        # Check terrain is not water
        start_tile = game.map.tiles.get(position)
        if start_tile is None:
            self._event_log.add_event("Cannot settle on this terrain", "error")
            return
        if start_tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
            self._event_log.add_event("Cannot settle on water tiles", "error")
            return

        # Create new city
        city_name = f"{game.player_civ.name} Colony"
        counter = 1
        while city_name in game.cities:
            counter += 1
            city_name = f"{game.player_civ.name} Colony {counter}"
        from game_data import get_climate_for_row
        climate = get_climate_for_row(position[1], game.map.height)
        is_coastal = start_tile.terrain in (TerrainType.WATER_COAST,)
        from city import City
        new_city = City(
            name=city_name,
            owner=game.player_civ.name,
            position=position,
            population=1,
            gold=0,
            climate_zone=climate,
            is_coastal=is_coastal,
        )
        game.cities[new_city.name] = new_city
        game.map.add_city(new_city)
        game.city_manager.cities = list(game.cities.values())
        # Remove Settler (it becomes the city)
        game.military_manager.remove_unit(unit)
        if unit.name in game.units:
            del game.units[unit.name]
        self._event_log.add_event(f"Founded {new_city.name}!", "success")
        self._selected_unit = None
        self._action_bar.set_mode("default")
        self._hex_renderer.selected_hex = None
        self._hex_renderer.move_range.clear()
        self._unit_panel.refresh(game)
        self._city_panel.refresh(game)

    def _show_production(self, game, city=None) -> None:
        """Show production popup for selected city."""
        from pygame_app.popups.production import ProductionPopup
        popup = ProductionPopup()
        popup.show(self.ui_manager, city, game)
        self._production_popup = popup
        self._active_popup = popup

    def _open_production_popup(self, game, city) -> None:
        """Open production popup for a specific city."""
        self._show_production(game, city)

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

        # Update hex renderer animations
        if self._hex_renderer:
            self._hex_renderer.update(dt)
            self._elapsed += dt

        # Refresh side panels
        game = self.app.game
        if self._city_panel:
            self._city_panel.refresh(game)
        if self._unit_panel:
            self._unit_panel.refresh(game)

    def _check_needs_attention(self, game) -> bool:
        """Check if any player units have moves left or cities need production."""
        civ_name = game.player_civ.name
        # Check units with moves
        for unit in game.units.values():
            if unit.owner == civ_name and unit.is_alive and getattr(unit, "moves_left", 0) > 0:
                return True
        # Check cities with production queue
        for city in game.cities.values():
            if city.owner == civ_name and getattr(city, "production_queue", None):
                return True
        return False

    def draw(self, surface):
        game = self.app.game

        # ── Panel backgrounds (dark) ──────────────────────────────────────
        # Top resource bar
        surface.fill(PANEL_BG, pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))
        # Bottom action bar
        surface.fill(PANEL_BG, pygame.Rect(0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT,
                                           SCREEN_WIDTH, ACTION_BAR_HEIGHT))
        # Left panel
        surface.fill(PANEL_BG, pygame.Rect(0, RESOURCE_BAR_HEIGHT,
                                           LEFT_PANEL_WIDTH,
                                           SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        # Right panel
        surface.fill(PANEL_BG, pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT,
                                           RIGHT_PANEL_WIDTH,
                                           SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))

        # ── Gold border lines ─────────────────────────────────────────────
        gold = (197, 160, 89)
        # Top bar bottom border (gold)
        pygame.draw.line(surface, gold, (0, RESOURCE_BAR_HEIGHT - 1),
                         (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT - 1), 1)
        # Bottom bar top border (gold)
        bar_y = SCREEN_HEIGHT - ACTION_BAR_HEIGHT
        pygame.draw.line(surface, gold, (0, bar_y),
                         (SCREEN_WIDTH, bar_y), 1)
        # Left panel right border (gold)
        pygame.draw.line(surface, gold,
                         (LEFT_PANEL_WIDTH - 1, RESOURCE_BAR_HEIGHT),
                         (LEFT_PANEL_WIDTH - 1, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), 1)
        # Right panel left border (gold)
        rx = SCREEN_WIDTH - RIGHT_PANEL_WIDTH
        pygame.draw.line(surface, gold,
                         (rx, RESOURCE_BAR_HEIGHT),
                         (rx, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), 1)
        # Map area borders (gold)
        pygame.draw.line(surface, gold, (MAP_X, MAP_Y - 1), (MAP_X + MAP_W, MAP_Y - 1), 1)
        pygame.draw.line(surface, gold, (MAP_X, MAP_Y + MAP_H),
                         (MAP_X + MAP_W, MAP_Y + MAP_H), 1)
        pygame.draw.line(surface, gold, (MAP_X - 1, MAP_Y),
                         (MAP_X - 1, MAP_Y + MAP_H), 1)
        pygame.draw.line(surface, gold, (MAP_X + MAP_W, MAP_Y),
                         (MAP_X + MAP_W, MAP_Y + MAP_H), 1)

        # ── Draw resource bar with custom text ────────────────────────────
        if self._resource_bar:
            self._resource_bar.draw(surface, game)

        # ── Draw action bar with custom buttons ───────────────────────────
        if self._action_bar:
            needs_attention = self._check_needs_attention(game)
            self._action_bar.set_needs_attention(needs_attention)
            self._action_bar.draw(surface)

        # ── Draw side panels ──────────────────────────────────────────────
        if self._city_panel:
            self._city_panel.draw(surface)
        if self._unit_panel:
            self._unit_panel.draw(surface)
        if self._event_log:
            self._event_log.draw(surface)

        # ── Map surface ───────────────────────────────────────────────────
        self._map_surface.fill(BG)
        if self._hex_renderer:
            self._hex_renderer.render(self._map_surface, game, self._elapsed)
        surface.blit(self._map_surface, (MAP_X, MAP_Y))

        # ── Minimap ───────────────────────────────────────────────────────
        if self._minimap:
            self._minimap.render(surface, game, SCREEN_HEIGHT)
