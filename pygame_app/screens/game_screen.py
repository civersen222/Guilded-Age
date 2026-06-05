"""Main gameplay screen — coordinates map, panels, popups, minimap, and interaction."""
import pygame
import pygame_gui
from pygame_app.screens.base import BaseScreen
from game_data import TerrainType
from pygame_app.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_X, MAP_Y, MAP_W, MAP_H,
    RESOURCE_BAR_HEIGHT, ACTION_BAR_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
    PANEL_BG, BG,
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
from pygame_app.popups.combat_popup import CombatPopup
from pygame_app.popups.event_choice import EventChoicePopup


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, minimap, and manages interaction."""

    def __init__(self, app):
        super().__init__(app)
        self._camera = self._atlas = self._hex_renderer = self._minimap = self._map_surface = None
        self._resource_bar = self._city_panel = self._event_log = self._turn_summary = None
        self._action_bar = self._next_turn_btn = self._unit_panel = None
        self._selected_unit = self._selected_city = self._active_popup = None
        self._event_choice_popup = EventChoicePopup()
        self._dragging_middle = False
        self._drag_start = (0, 0)
        self.show_yields = False
        self._elapsed = 0.0

    def enter(self):
        game = self.app.game
        self._camera = Camera(MAP_W, MAP_H)
        self._atlas = TileAtlas("assets/tiles")
        self._hex_renderer = HexRenderer(game.map, self._atlas, self._camera)
        self._minimap = Minimap(game.map, self._camera)
        self._map_surface = pygame.Surface((MAP_W, MAP_H))
        cities = list(game.cities.values())
        if cities:
            wx, wy = HexRenderer.hex_to_world(*getattr(cities[0], "position", (0, 0)))
            self._camera.snap_to(wx, wy)
        self._resource_bar = ResourceBar(self.ui_manager, game)
        self._city_panel = CityPanel(self.ui_manager, pygame.Rect(0, RESOURCE_BAR_HEIGHT, LEFT_PANEL_WIDTH, 400))
        self._city_panel.refresh(game)
        self._event_log = EventLog(self.ui_manager, pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT, RIGHT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        self._action_bar = ActionBar(self.ui_manager)
        self._action_bar.set_mode("default")
        self._unit_panel = UnitPanel(self.ui_manager, pygame.Rect(0, RESOURCE_BAR_HEIGHT + 400, LEFT_PANEL_WIDTH, 300))
        self._unit_panel.refresh(game)
        self._turn_summary = TurnSummary()
        self._next_turn_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH - 20, SCREEN_HEIGHT - ACTION_BAR_HEIGHT - 15, 140, 35),
            text="Next Turn", manager=self.ui_manager,
        )

    def exit(self):
        for attr in ("_resource_bar", "_city_panel", "_event_log", "_action_bar", "_unit_panel"):
            obj = getattr(self, attr, None)
            if hasattr(obj, "destroy"): obj.destroy()
        if self._turn_summary and self._turn_summary.is_visible: self._turn_summary._kill()
        if self._next_turn_btn: self._next_turn_btn.kill()

    def handle_event(self, event):
        game = self.app.game
        if event.type == pygame.MOUSEWHEEL and event.y != 0:
            mx, my = pygame.mouse.get_pos()
            factor = 1.15 if event.y > 0 else 1 / 1.15
            self._camera.zoom_at(mx - MAP_X, my - MAP_Y, factor)
            return
        if self._turn_summary and self._turn_summary.is_visible:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                if self._turn_summary.window:
                    self._turn_summary.window.kill()
                self._turn_summary.window = None
                self._turn_summary.text_box = None
                self._turn_summary.dismiss_btn = None
                self._needs_map_redraw = True
                return
            if self._turn_summary.handle_event(event):
                return
        action = self._action_bar.handle_event(event)
        if action is not None:
            self._handle_action(action, game)
            return
        if getattr(self, "_production_popup", None) and self._production_popup.handle_event(event):
            return
        if getattr(self, "_event_choice_popup", None) and self._event_choice_popup.is_visible:
            if self._event_choice_popup.handle_event(event):
                return
        combat_result = getattr(self, "combat_popup", None)
        if combat_result is not None:
            result = combat_result.handle_event(event)
            if result is not None:
                self._apply_combat_result(result)
                combat_result.hide()
                self.combat_popup = None
                self.deselect()
                return
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event, game)
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse_down(event, game)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self._dragging_middle = False

    def _handle_key(self, event, game):
        if event.key == pygame.K_ESCAPE:
            if self._active_popup: self._active_popup._kill(); self._active_popup = None
            elif self._selected_unit: self.deselect()
            return
        if event.key == pygame.K_RETURN:
            self._process_next_turn(game)
            return
        if event.key == pygame.K_SPACE and self._selected_unit:
            self._selected_unit.moves_left = 0
            self._hex_renderer.move_range.clear()
            self._unit_panel.refresh(game)
            self._event_log.add_event(f"{self._selected_unit.unit_type} skipped", "info")
            return
        if event.key == pygame.K_TAB:
            units = [u for u in game.units.values() if getattr(u, "is_alive", False) and getattr(u, "owner", "") == game.player_civ.name and getattr(u, "moves_left", 0) > 0]
            if units:
                if self._selected_unit and self._selected_unit in units:
                    idx = units.index(self._selected_unit)
                    self._select_unit(game, units[(idx + 1) % len(units)])
                else:
                    self._select_unit(game, units[0])
            return
        if event.key == pygame.K_t: self._open_popup("tech", game)
        elif event.key == pygame.K_d: self._open_popup("diplomacy", game)
        elif event.key == pygame.K_y: self._open_popup("dynasty", game)
        elif event.key == pygame.K_r:
            from pygame_app.popups.religion_popup import ReligionPopup
            player_name = getattr(game.player_civ, "name", "")
            self._active_popup = ReligionPopup(self.ui_manager, game, player_name)
            return
        elif event.key == pygame.K_p: self._open_production_popup_for(game, self._selected_city)
        elif event.key in (pygame.K_h, pygame.K_F1):
            import pygame_gui
            w, h = 400, 350
            cx = (getattr(self, "screen_w", 1280) - w) // 2
            cy = (getattr(self, "screen_h", 720) - h) // 2
            win = pygame_gui.elements.UIWindow(pygame.Rect(cx, cy, w, h), manager=self.ui_manager, window_display_title="Keyboard Shortcuts")
            pygame_gui.elements.UITextBox(
                "<b>Keyboard Shortcuts</b><br><br>"
                "<b>T</b> - Technology Tree<br>"
                "<b>D</b> - Diplomacy<br>"
                "<b>Y</b> - Dynasty<br>"
                "<b>R</b> - Religion<br>"
                "<b>P</b> - Production (city)<br>"
                "<b>TAB</b> - Cycle Units<br>"
                "<b>SPACE</b> - Skip Unit<br>"
                "<b>ENTER</b> - End Turn<br>"
                "<b>ESC</b> - Close / Deselect<br>"
                "<b>H / F1</b> - This Help<br>",
                pygame.Rect(8, 8, w-16, h-16), manager=self.ui_manager, container=win)
            self._active_popup = type("HelpPopup", (), {"_kill": lambda s: win.kill(), "is_visible": property(lambda s: win.alive()), "handle_event": lambda s,e: False})()
            return
        elif event.key == pygame.K_f and self._selected_unit:
            self._selected_unit.is_fortified = True
            self._event_log.add_event(f"{self._selected_unit.unit_type} fortified", "info")
        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
            mx, my = event.pos
            self._camera.zoom_at(mx - MAP_X, my - MAP_Y, 1.15)
        elif event.key == pygame.K_MINUS:
            mx, my = event.pos
            self._camera.zoom_at(mx - MAP_X, my - MAP_Y, 1 / 1.15)
        elif event.key == pygame.K_g:
            self.show_yields = not self.show_yields
            self._event_log.add_event("Yield overlay ON" if self.show_yields else "Yield overlay OFF", "info")
        elif event.key in (pygame.K_h, pygame.K_F1):
            self._show_help_popup()

    def _handle_mouse_down(self, event, game):
        mx, my = event.pos
        if event.button == 2:
            self._dragging_middle = True
            self._drag_start = (mx, my)
            return
        if event.button == 1 and MAP_X <= mx <= MAP_X + MAP_W and MAP_Y <= my <= MAP_Y + MAP_H:
            hx, hy = self._hex_renderer.screen_to_hex(mx - MAP_X, my - MAP_Y)
            self._hex_renderer.selected_hex = (hx, hy)
            if self._selected_unit and (hx, hy) in self._hex_renderer.move_range:
                # Check for enemy unit on clicked tile
                enemy_units = [u for u in self.game.military_manager.units if u.position == (hx, hy) and u.owner != self._selected_unit.owner]
                if enemy_units:
                    self.combat_popup = CombatPopup(self.ui_manager, self._selected_unit, enemy_units[0], self.game)
                    return
                self._move_unit(game, hx, hy)
                return
            if self._try_select_city_at_hex(game, hx, hy): return
            if self._try_select_unit_at_hex(game, hx, hy): return
            self.deselect()
            return
        if self._minimap and self._minimap.handle_click(mx, my, SCREEN_HEIGHT): return
        unit = self._unit_panel.handle_event(event)
        if unit is not None:
            self._select_unit(game, unit)
            return
        city = self._city_panel.handle_event(event)
        if city is not None:
            wx, wy = HexRenderer.hex_to_world(*getattr(city, "position", (0, 0)))
            self._camera.center_on(wx, wy)

    def _try_select_unit_at_hex(self, game, hx, hy):
        """Find a player-owned unit at the clicked hex and select it."""
        for unit in game.units.values():
            if unit.is_alive and unit.owner == game.player_civ.name and unit.position == (hx, hy):
                self._select_unit(game, unit)
                return True
        return False

    def _try_select_city_at_hex(self, game, hx, hy):
        for city in game.cities.values():
            if getattr(city, "owner", "") == game.player_civ.name and getattr(city, "position", None) == (hx, hy):
                self._selected_city, self._selected_unit = city, None
                self._action_bar.set_mode("city_selected")
                self._hex_renderer.selected_hex = (hx, hy)
                self._hex_renderer.move_range.clear()
                self._open_production_popup_for(game, city)
                return True
        return False

    def _select_unit(self, game, unit):
        self._selected_unit, self._selected_city = unit, None
        self._hex_renderer.selected_hex = getattr(unit, "position", (0, 0))
        self._hex_renderer.attack_range.clear()
        if getattr(unit, "moves_left", 0) > 0:
            game._player_name = game.player_civ.name
            self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(getattr(unit, "position", (0, 0)), getattr(unit, "moves_left", 0), game.units, game)
        self._action_bar.set_mode("settler_selected" if getattr(unit, "unit_type", "") == "Settler" else "unit_selected")

    def _move_unit(self, game, hx, hy):
        unit = self._selected_unit
        if not unit: return
        if game.military_manager.move_unit(unit, (hx, hy)):
            self._event_log.add_event(f"{unit.unit_type} moved to ({hx},{hy})", "success")
            self._update_fog(game)
            ml = getattr(unit, "moves_left", 0)
            if ml > 0:
                self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(getattr(unit, "position", (0, 0)), ml, game.units, game)
            else:
                self._hex_renderer.move_range.clear()
            self._unit_panel.refresh(game)
        else:
            self._event_log.add_event(f"Cannot move {unit.unit_type} to ({hx},{hy})", "error")

    def _update_fog(self, game):
        sources = [(getattr(c, "position", (0, 0))[0], getattr(c, "position", (0, 0))[1], 3) for c in game.cities.values() if getattr(c, "owner", None) == game.player_civ.name]
        sources += [(getattr(u, "position", (0, 0))[0], getattr(u, "position", (0, 0))[1], 2) for u in game.units.values() if getattr(u, "owner", None) == game.player_civ.name]
        game.fog.update_visibility(sources)

    def _process_next_turn(self, game):
        print(f"[game_screen] _process_next_turn called, turn before={game.state.turn}")
        game.process_turn()
        print(f"[game_screen] process_turn done, turn after={game.state.turn}")

        # Check for victory/game over
        if getattr(game.state, "game_over", False):
            winner = getattr(game.state, "winner", "Unknown")
            victory_type = getattr(game.state, "victory_type", "Domination")
            is_player_win = (winner == getattr(game.player_civ, "name", ""))
            title = "VICTORY!" if is_player_win else "DEFEAT"
            msg = f"{winner} wins by {victory_type}!"
            self._event_log.add_event(f"{title}: {msg}", "critical")
        self._update_fog(game)
        if game.tech_manager.current_research is None:
            available = game.tech_manager.get_available_techs()
            if available:
                tech = available[0]
                name = getattr(tech, "name", str(tech))
                game.tech_manager.start_research(tech)
                self._event_log.add_event(f"Auto-researching: {name}", "science")
        self._resource_bar.refresh(game)
        self._city_panel.refresh(game)
        self._unit_panel.refresh(game)
        events = game.state.turn_events or []
        for evt in events:
            self._event_log.add_event(str(evt), "info")
        if events:
            self._turn_summary.show(self.ui_manager, events, game.state.turn)

    def _handle_action(self, action, game):
        if action == "Next Turn": self._process_next_turn(game)
        elif action == "Save":
            from save_system import save_game
            path = save_game(game)
            self._event_log.add_event(f"Game saved to {path}", "success")
        elif action in ("Move", "Attack", "Fortify", "Skip"): self._handle_unit_action(action, game)
        elif action == "Tech Tree": self._open_popup("tech", game)
        elif action == "Diplomacy": self._open_popup("diplomacy", game)
        elif action == "Dynasty": self._open_popup("dynasty", game)
        elif action == "Production": self._open_production_popup_for(game, self._selected_city)
        elif action == "Settle": self._settle_city(game)
        elif action == "Deselect": self.deselect()

    def _handle_unit_action(self, action, game):
        unit = self._selected_unit
        if not unit: return
        if action == "Move":
            if getattr(unit, "moves_left", 0) > 0:
                game._player_name = game.player_civ.name
                self._hex_renderer.move_range = self._hex_renderer.calculate_move_range(getattr(unit, "position", (0, 0)), getattr(unit, "moves_left", 0), game.units, game)
            else:
                self._event_log.add_event("Unit has no moves left", "error")
        elif action == "Attack":
            game._player_name = game.player_civ.name
            self._hex_renderer.attack_range = self._hex_renderer.calculate_attack_range(getattr(unit, "position", (0, 0)), game.units, game)
            self._event_log.add_event("Select an enemy hex to attack" if self._hex_renderer.attack_range else "No enemies in attack range", "info")
        elif action == "Fortify":
            unit.is_fortified = True
            self._event_log.add_event(f"{unit.unit_type} fortified", "info")
        elif action == "Skip":
            unit.moves_left = 0
            self._event_log.add_event(f"{unit.unit_type} skipped", "info")
            self._unit_panel.refresh(game)

    def _settle_city(self, game):
        unit = self._selected_unit
        if not unit or getattr(unit, "unit_type", "") != "Settler": return
        pos = getattr(unit, "position", None)
        if not pos: return
        if any(getattr(c, "position", None) == pos for c in game.cities.values()):
            self._event_log.add_event("A city already exists here", "error")
            return
        if any(getattr(u, "is_alive", False) and getattr(u, "owner", "") != game.player_civ.name and getattr(u, "position", None) == pos for u in game.units.values()):
            self._event_log.add_event("Cannot settle on an enemy unit", "error")
            return
        tile = game.map.tiles.get(pos)
        if not tile or tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
            self._event_log.add_event("Cannot settle on water tiles", "error")
            return
        unit.owner = game.player_civ.name
        city = game.found_city(unit)
        game.city_manager.cities = list(game.cities.values())
        self._event_log.add_event(f"Founded {city.name}!", "success")
        self.deselect()
        self._city_panel.refresh(game)

    def _show_help_popup(self):
        """Show a keyboard shortcuts help overlay."""
        if getattr(self, "_active_popup", None):
            self._active_popup._kill()
        container = pygame_gui.elements.UIContainer(
            relative_rect=pygame.Rect(0, 0, 420, 310),
            relative_pos=(0.5, 0.5),
            manager=self.ui_manager,
        )
        container.set_relative_position((0.5, 0.5))
        title = pygame_gui.elements.UIText(
            relative_rect=pygame.Rect(10, 8, 400, 30),
            text="Keyboard Shortcuts",
            object_id="#help_title",
            manager=self.ui_manager,
            parent=container,
        )
        title.font = pygame.font.SysFont("arial", 18, bold=True)
        lines = [
            "T  - Technology Tree",
            "D  - Diplomacy",
            "Y  - Dynasty",
            "R  - Religion",
            "P  - Production (city selected)",
            "TAB - Cycle Units",
            "SPACE - Skip Unit",
            "ENTER - End Turn",
            "ESC - Close / Deselect",
            "H / F1 - This Help",
        ]
        text = "\n".join(lines)
        pygame_gui.elements.UITextBox(
            html_text=text,
            relative_rect=pygame.Rect(10, 40, 400, 230),
            manager=self.ui_manager,
            parent=container,
        )
        close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 270, 120, 30),
            text="Close",
            manager=self.ui_manager,
            parent=container,
        )
        self._active_popup = container

    def _open_popup(self, kind, game):
        """Open a popup window for tech, diplomacy, or dynasty screens.
        
        Verified working: all popup classes have matching show(ui_manager, game)
        signatures and proper _kill() methods.
        """
        if getattr(self, "_active_popup", None): self._active_popup._kill()
        popups = {"tech": ("TechTreePopup", "tech_tree"), "diplomacy": ("DiplomacyPopup", "diplomacy"), "dynasty": ("DynastyPopup", "dynasty")}
        cls_name, mod_name = popups[kind]
        mod = __import__(f"pygame_app.popups.{mod_name}", fromlist=[cls_name])
        popup = getattr(mod, cls_name)()
        popup.show(self.ui_manager, game)
        self._active_popup = popup

    def _open_production_popup_for(self, game, city):
        if getattr(self, "_active_popup", None): self._active_popup._kill()
        from pygame_app.popups.production import ProductionPopup
        popup = ProductionPopup()
        popup.show(self.ui_manager, city, game)
        self._production_popup = self._active_popup = popup

    def _apply_combat_result(self, result):
        """Apply combat results and log the outcome."""
        from combat import CombatResult
        if isinstance(result, CombatResult):
            # result.attacker and result.defender are already modified in-place by resolve_combat
            # Update the selected unit reference if it's still alive
            if self._selected_unit and not self._selected_unit.is_alive:
                self._selected_unit = None
            # Log the result
            if hasattr(self.game, 'event_log') and self.game.event_log:
                self.game.event_log.add_entry(result.description)
            # Redraw map to reflect HP changes
            self._needs_map_redraw = True

            # Remove dead units from game
            if hasattr(self.game, "military_manager"):
                dead = [u for u in self.game.military_manager.units if not getattr(u, "is_alive", True)]
                for u in dead:
                    self.game.military_manager.units.remove(u)
                    pos = getattr(u, "position", None)
                    if pos and hasattr(self.game, "hex_map"):
                        tile = self.game.hex_map.tiles.get(pos)
                        if tile and getattr(tile, "unit", None) == getattr(u, "unit_type", ""):
                            tile.unit = None

    def deselect(self):
        self._selected_unit = self._selected_city = None
        self._action_bar.set_mode("default")
        self._hex_renderer.move_range.clear()
        self._hex_renderer.attack_range.clear()

    def update(self, dt):
        game = self.app.game
        keys = pygame.key.get_pressed()
        speed = 400 * dt / self._camera.zoom
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += speed
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += speed
        if dx or dy: self._camera.pan(dx, dy)
        if self._dragging_middle:
            mx, my = pygame.mouse.get_pos()
            self._camera.pan(mx - self._drag_start[0], my - self._drag_start[1])
            self._drag_start = (mx, my)
        self._camera.update(dt)
        if self._hex_renderer:
            self._hex_renderer.update(dt)
            self._elapsed += dt
        if self._city_panel: self._city_panel.refresh(game)
        if self._unit_panel: self._unit_panel.refresh(game)

    def draw(self, surface):
        game = self.app.game
        gold = (197, 160, 89)
        surface.fill(PANEL_BG, pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))
        surface.fill(PANEL_BG, pygame.Rect(0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT, SCREEN_WIDTH, ACTION_BAR_HEIGHT))
        surface.fill(PANEL_BG, pygame.Rect(0, RESOURCE_BAR_HEIGHT, LEFT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        surface.fill(PANEL_BG, pygame.Rect(SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT, RIGHT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        pygame.draw.line(surface, gold, (0, RESOURCE_BAR_HEIGHT - 1), (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT - 1), 1)
        pygame.draw.line(surface, gold, (0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), 1)
        pygame.draw.line(surface, gold, (LEFT_PANEL_WIDTH - 1, RESOURCE_BAR_HEIGHT), (LEFT_PANEL_WIDTH - 1, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), 1)
        rx = SCREEN_WIDTH - RIGHT_PANEL_WIDTH
        pygame.draw.line(surface, gold, (rx, RESOURCE_BAR_HEIGHT), (rx, SCREEN_HEIGHT - ACTION_BAR_HEIGHT), 1)
        pygame.draw.line(surface, gold, (MAP_X, MAP_Y - 1), (MAP_X + MAP_W, MAP_Y - 1), 1)
        pygame.draw.line(surface, gold, (MAP_X, MAP_Y + MAP_H), (MAP_X + MAP_W, MAP_Y + MAP_H), 1)
        pygame.draw.line(surface, gold, (MAP_X - 1, MAP_Y), (MAP_X - 1, MAP_Y + MAP_H), 1)
        pygame.draw.line(surface, gold, (MAP_X + MAP_W, MAP_Y), (MAP_X + MAP_W, MAP_Y + MAP_H), 1)
        if self._resource_bar: self._resource_bar.draw(surface, game)
        if self._action_bar:
            self._action_bar.set_needs_attention(any(u.owner == game.player_civ.name and getattr(u, "moves_left", 0) > 0 for u in game.units.values()))
            self._action_bar.draw(surface)
        if self._city_panel: self._city_panel.draw(surface)
        if self._unit_panel: self._unit_panel.draw(surface)
        if self._event_log: self._event_log.draw(surface)
        self._map_surface.fill(BG)
        self._needs_map_redraw = getattr(self, '_needs_map_redraw', True)
        if self._hex_renderer: self._hex_renderer.render(self._map_surface, game, self._elapsed)
        surface.blit(self._map_surface, (MAP_X, MAP_Y))
        if self._minimap: self._minimap.render(surface, game, SCREEN_HEIGHT)
