"""Left sidebar panel — lists all player units with status."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT


class UnitPanel:
    """Left sidebar listing player units."""

    PANEL_HEIGHT = 300
    UNIT_BTN_HEIGHT = 32
    MARGIN = 4

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
        )
        self.unit_buttons: Dict[pygame_gui.elements.UIButton, Any] = {}

    def refresh(self, game: Any) -> None:
        """Rebuild unit buttons from current game state."""
        for btn in list(self.unit_buttons.keys()):
            btn.kill()
        self.unit_buttons.clear()

        player_units = [u for u in game.units.values() if u.owner == game.player_civ.name]

        y = self.MARGIN
        for unit in player_units:
            hp = getattr(unit, "hp", 0)
            max_hp = getattr(unit, "max_hp", 0)
            moves = getattr(unit, "moves_left", 0)
            unit_type = getattr(unit, "unit_type", "Unknown")

            prefix = "* " if moves > 0 else "  "
            text = f"{prefix}{unit_type} HP:{hp}/{max_hp} Mv:{moves}"

            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    self.MARGIN, y,
                    LEFT_PANEL_WIDTH - self.MARGIN * 2,
                    self.UNIT_BTN_HEIGHT,
                ),
                text=text,
                manager=self.ui_manager,
                container=self.panel,
            )
            self.unit_buttons[btn] = unit
            y += self.UNIT_BTN_HEIGHT + self.MARGIN

    def handle_event(self, event) -> Optional[Any]:
        """If a unit button was pressed, return the unit. Otherwise None."""
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and event.ui_element in self.unit_buttons):
            return self.unit_buttons[event.ui_element]
        return None

    def destroy(self) -> None:
        """Kill panel and all child buttons."""
        for btn in self.unit_buttons.keys():
            btn.kill()
        self.unit_buttons.clear()
        self.panel.kill()
