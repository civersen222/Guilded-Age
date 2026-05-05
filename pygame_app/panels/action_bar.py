"""Bottom bar — context-sensitive action buttons."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import ACTION_BAR_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH


ACTION_BUTTONS = {
    "default": [
        ("Next Turn", "Next Turn"),
        ("Tech Tree", "Tech Tree"),
        ("Diplomacy", "Diplomacy"),
        ("Save", "Save"),
    ],
    "unit_selected": [
        ("Move", "Move"),
        ("Attack", "Attack"),
        ("Fortify", "Fortify"),
        ("Skip", "Skip"),
    ],
    "city_selected": [
        ("Production", "Production"),
    ],
}


class ActionBar:
    """Bottom bar with context-sensitive action buttons."""

    BUTTON_W = 100
    BUTTON_H = 35
    SPACING = 110
    START_X = 10

    def __init__(self, ui_manager: pygame_gui.UIManager):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT,
                                      SCREEN_WIDTH, ACTION_BAR_HEIGHT),
            manager=ui_manager,
        )
        self.buttons: Dict[str, pygame_gui.elements.UIButton] = {}
        self.mode: str = "default"

    def set_mode(self, mode: str, context: Any = None) -> None:
        """Switch action bar mode and rebuild buttons."""
        self._kill_buttons()
        self.mode = mode
        actions = ACTION_BUTTONS.get(mode, ACTION_BUTTONS["default"])
        y = (ACTION_BAR_HEIGHT - self.BUTTON_H) // 2

        for i, (label, action) in enumerate(actions):
            x = self.START_X + i * self.SPACING
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(x, y, self.BUTTON_W, self.BUTTON_H),
                text=label,
                manager=self.ui_manager,
                container=self.panel,
            )
            self.buttons[action] = btn

    def handle_event(self, event) -> Optional[str]:
        """If a button was pressed, return its action name. Otherwise None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for action, btn in self.buttons.items():
                if event.ui_element == btn:
                    return action
        return None

    def _kill_buttons(self) -> None:
        """Remove all existing action buttons."""
        for btn in self.buttons.values():
            btn.kill()
        self.buttons.clear()

    def destroy(self) -> None:
        """Kill all buttons and the panel."""
        self._kill_buttons()
        self.panel.kill()
