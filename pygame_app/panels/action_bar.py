"""Bottom bar — context-sensitive action buttons."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import (
    ACTION_BAR_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH,
    PANEL_BG, GOLD, RED as RED_COLOR, BORDER,
)

GOLD_TEXT = (197, 160, 89)
WHITE_TEXT = (255, 255, 255)
BTN_BG = (35, 38, 45)
BTN_HOVER = (50, 54, 65)
BTN_BORDER = (51, 54, 61)
NEXT_TURN_GOLD = (197, 160, 89)
NEXT_TURN_RED = (178, 58, 58)


ACTION_BUTTONS = {
    "default": [
        ("Next Turn", "Next Turn"),
        ("Tech Tree", "Tech Tree"),
        ("Diplomacy", "Diplomacy"),
        ("Dynasty", "Dynasty"),
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

    BUTTON_W = 120
    BUTTON_H = 36
    SPACING = 130
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
        self._font = pygame.font.SysFont("consolas", 12, bold=True)
        self._next_turn_color = NEXT_TURN_GOLD
        self._needs_attention = False

    def set_needs_attention(self, needs_attention: bool) -> None:
        """Set whether the Next Turn button should show red."""
        self._needs_attention = needs_attention
        self._next_turn_color = NEXT_TURN_RED if needs_attention else NEXT_TURN_GOLD

    def needs_attention(self) -> bool:
        """Check if units/cities need attention."""
        return self._needs_attention

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

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the polished action bar background and buttons."""
        # Dark background
        surface.fill(PANEL_BG, pygame.Rect(0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT,
                                           SCREEN_WIDTH, ACTION_BAR_HEIGHT))

        # Gold border at top
        pygame.draw.line(surface, GOLD_TEXT, (0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT),
                         (SCREEN_WIDTH, SCREEN_HEIGHT - ACTION_BAR_HEIGHT))

        # Draw custom buttons
        actions = ACTION_BUTTONS.get(self.mode, ACTION_BUTTONS["default"])

        # Track which action we're drawing to handle Next Turn specially
        for i, (label, action) in enumerate(actions):
            x = self.START_X + i * self.SPACING
            y = (ACTION_BAR_HEIGHT - self.BUTTON_H) // 2

            # Next Turn button — prominent with color coding
            if action == "Next Turn":
                btn_color = self._next_turn_color
                # Draw button background with gold/red tint
                btn_rect = pygame.Rect(x, y, self.BUTTON_W, self.BUTTON_H)
                pygame.draw.rect(surface, btn_color, btn_rect, border_radius=4)
                # Dark inner
                inner = btn_rect.inflate(-4, -4)
                pygame.draw.rect(surface, PANEL_BG, inner, border_radius=3)
                # Gold text
                rendered = self._font.render(label, True, btn_color)
                tx = x + (self.BUTTON_W - rendered.get_width()) // 2
                ty = y + (self.BUTTON_H - rendered.get_height()) // 2
                surface.blit(rendered, (tx, ty))
            else:
                # Standard button
                btn_rect = pygame.Rect(x, y, self.BUTTON_W, self.BUTTON_H)
                pygame.draw.rect(surface, BTN_BG, btn_rect, border_radius=4)
                inner = btn_rect.inflate(-2, -2)
                pygame.draw.rect(surface, BTN_BORDER, inner, border_radius=3)
                rendered = self._font.render(label, True, WHITE_TEXT)
                tx = x + (self.BUTTON_W - rendered.get_width()) // 2
                ty = y + (self.BUTTON_H - rendered.get_height()) // 2
                surface.blit(rendered, (tx, ty))

    def destroy(self) -> None:
        """Kill all buttons and the panel."""
        self._kill_buttons()
        self.panel.kill()
