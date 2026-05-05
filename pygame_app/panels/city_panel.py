"""Left sidebar panel — lists all player cities with production info."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import (
    LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT,
    PANEL_BG, GOLD, GREEN, RED, SUBTLE,
)

GOLD_TEXT = (197, 160, 89)
WHITE_TEXT = (255, 255, 255)
BTN_BG = (30, 32, 40)
BTN_HIGHLIGHT = (40, 44, 55)


class CityPanel:
    """Left sidebar listing player cities."""

    PANEL_HEIGHT = 400
    CITY_BTN_HEIGHT = 40
    MARGIN = 4

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
            start_surface=None,
        )
        self.panel.get_container().set_alpha(0.0)
        self.city_buttons: Dict[pygame_gui.elements.UIButton, Any] = {}
        self._font = pygame.font.SysFont("consolas", 11)
        self._font_bold = pygame.font.SysFont("consolas", 11, bold=True)

    def refresh(self, game: Any) -> None:
        """Rebuild city buttons from current game state."""
        for btn in list(self.city_buttons.keys()):
            btn.kill()
        self.city_buttons.clear()

        player_civ_name = game.player_civ.name
        cities = [c for c in game.cities.values() if c.owner == player_civ_name]

        y = self.MARGIN
        for city in cities:
            name = getattr(city, "name", "Unnamed")
            pop = getattr(city, "population", 0)
            prod = getattr(city, "current_production", None)
            prod_name = getattr(prod, "name", "IDLE") if prod else "IDLE"

            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    self.MARGIN, y,
                    LEFT_PANEL_WIDTH - self.MARGIN * 2,
                    self.CITY_BTN_HEIGHT,
                ),
                text="",
                manager=self.ui_manager,
                container=self.panel,
            )
            btn.set_alpha(0.0)
            self.city_buttons[btn] = city
            y += self.CITY_BTN_HEIGHT + self.MARGIN

    def draw(self, surface: pygame.Surface) -> None:
        """Draw custom city panel with polished UI."""
        # Gold border at top
        y_pos = self.panel.get_abs_position()[1]
        w = self.panel.get_abs_position()[0] + self.panel.get_rect().width
        pygame.draw.line(surface, GOLD_TEXT, (0, y_pos), (w, y_pos), 1)

        # Draw each city entry
        for btn, city in self.city_buttons.items():
            rect = btn.get_rect().copy()
            rect.x += self.panel.get_abs_position()[0]
            rect.y += self.panel.get_abs_position()[1]

            # Button background
            pygame.draw.rect(surface, BTN_BG, rect, border_radius=3)

            # Gold accent line on left
            pygame.draw.line(surface, GOLD_TEXT, (rect.x + 2, rect.y + 4),
                             (rect.x + 2, rect.y + rect.height - 4), 2)

            # City name
            name = getattr(city, "name", "Unnamed")
            pop = getattr(city, "population", 0)
            prod = getattr(city, "current_production", None)
            prod_name = getattr(prod, "name", "IDLE") if prod else "IDLE"

            # Name in gold
            name_surf = self._font_bold.render(name, True, GOLD_TEXT)
            surface.blit(name_surf, (rect.x + 10, rect.y + 4))

            # Population in white
            pop_surf = self._font.render(f"Pop:{pop}", True, WHITE_TEXT)
            surface.blit(pop_surf, (rect.x + 10, rect.y + 20))

            # Production in subtle color
            prod_surf = self._font.render(f"→ {prod_name}", True, SUBTLE)
            px = rect.x + rect.width - prod_surf.get_width() - 10
            surface.blit(prod_surf, (px, rect.y + 20))

    def handle_event(self, event) -> Optional[Any]:
        """If a city button was pressed, return the city. Otherwise None."""
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and event.ui_element in self.city_buttons):
            return self.city_buttons[event.ui_element]
        return None

    def destroy(self) -> None:
        """Kill panel and all child buttons."""
        for btn in self.city_buttons.keys():
            btn.kill()
        self.city_buttons.clear()
        self.panel.kill()
