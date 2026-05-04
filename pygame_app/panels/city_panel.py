"""Left sidebar panel — lists all player cities with production info."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT


class CityPanel:
    """Left sidebar listing player cities."""

    PANEL_HEIGHT = 400
    CITY_BTN_HEIGHT = 36
    MARGIN = 4

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
        )
        self.city_buttons: Dict[pygame_gui.elements.UIButton, Any] = {}

    def refresh(self, game: Any) -> None:
        """Rebuild city buttons from current game state."""
        # Kill existing buttons
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

            text = f"{name} (Pop {pop}) - Building: {prod_name}"
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    self.MARGIN, y,
                    LEFT_PANEL_WIDTH - self.MARGIN * 2,
                    self.CITY_BTN_HEIGHT,
                ),
                text=text,
                manager=self.ui_manager,
                container=self.panel,
            )
            self.city_buttons[btn] = city
            y += self.CITY_BTN_HEIGHT + self.MARGIN

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
