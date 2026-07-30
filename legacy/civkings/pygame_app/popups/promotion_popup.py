"""Popup — promotion choice screen with three stat bonus buttons."""

from typing import Any, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 360
HEIGHT = 220
MARGIN = 10
BUTTON_W = 100
BUTTON_H = 36


class PromotionPopup:
    """Popup offering three promotion choices: +1 Attack, +1 Defense, +1 Movement."""

    def __init__(self, manager: pygame_gui.UIManager, unit: Any):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.unit = unit
        self._chosen: Optional[str] = None

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=manager,
            window_display_title=f"Promote {unit.name}",
        )

        # Description label
        desc = pygame_gui.elements.UITextBox(
            "Choose a promotion bonus:",
            pygame.Rect(MARGIN, MARGIN, WIDTH - 2 * MARGIN, 28),
            container=self.window,
        )

        btn_y = MARGIN + 40
        btn_spacing = (WIDTH - 2 * MARGIN - BUTTON_W * 3) // 2

        self.btn_attack = pygame_gui.elements.UIButton(
            pygame.Rect(MARGIN + btn_spacing, btn_y, BUTTON_W, BUTTON_H),
            "+1 Attack",
            manager=manager,
            container=self.window,
        )

        self.btn_defense = pygame_gui.elements.UIButton(
            pygame.Rect(MARGIN + btn_spacing + BUTTON_W + btn_spacing, btn_y, BUTTON_W, BUTTON_H),
            "+1 Defense",
            manager=manager,
            container=self.window,
        )

        self.btn_movement = pygame_gui.elements.UIButton(
            pygame.Rect(MARGIN + btn_spacing + 2 * (BUTTON_W + btn_spacing), btn_y, BUTTON_W, BUTTON_H),
            "+1 Movement",
            manager=manager,
            container=self.window,
        )

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Return chosen promotion key ('attack', 'defense', 'movement') or None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_attack:
                self._chosen = "attack"
            elif event.ui_element == self.btn_defense:
                self._chosen = "defense"
            elif event.ui_element == self.btn_movement:
                self._chosen = "movement"
        return self._chosen

    def hide(self):
        if self.window:
            self.window.kill()
