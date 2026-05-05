"""Popup — random event with player choices."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 450
HEIGHT = 400
MARGIN = 8
BUTTON_H = 30
BUTTON_W = 200


class EventChoicePopup:
    """Popup showing random events with player choices."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.desc_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.choice_buttons: List[pygame_gui.elements.UIButton] = []
        self._event: Any = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, event: Any, game: Any = None) -> None:
        """Show the event choice popup."""
        self._event = event
        self._game = game

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            relative_rect=pygame.Rect(cx, cy, WIDTH, HEIGHT),
            window_title=getattr(event, "name", "Event"),
            manager=ui_manager,
            window_type="modal",
        )

        # Description textbox
        desc = getattr(event, "description", "")
        self.desc_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2 - BUTTON_H - 20),
            html_text=f"<b>{desc}</b><br>",
            manager=ui_manager,
            container=self.window,
        )

        # Choices or OK button
        choices = getattr(event, "choices", [])
        if choices:
            y = MARGIN + 100
            for choice in choices:
                label = choice.get("name", "Choose")
                btn = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(MARGIN, y, BUTTON_W, BUTTON_H),
                    text=label,
                    manager=ui_manager,
                    container=self.window,
                )
                self.choice_buttons.append(btn)
                y += BUTTON_H + 6
        else:
            # Single OK button
            ok_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((WIDTH - 100) // 2, HEIGHT - BUTTON_H - MARGIN, 100, BUTTON_H),
                text="OK",
                manager=ui_manager,
                container=self.window,
            )
            self.choice_buttons.append(ok_btn)

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if self._event is None:
                return True

            choices = getattr(self._event, "choices", [])
            for i, btn in enumerate(self.choice_buttons):
                if event.ui_element == btn:
                    if choices and i < len(choices):
                        choice = choices[i]
                        self._event.evaluate_choice(choice)
                    elif not choices:
                        # No choices — apply default effects if any
                        effects = getattr(self._event, "effects", {})
                        if effects:
                            for effect_type, value in effects.items():
                                print(f"  Effect: {effect_type} {value}")
                    self._kill()
                    return True
            return True
        return False

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.desc_textbox] + self.choice_buttons:
            if elem is not None:
                elem.kill()
        self.desc_textbox = None
        self.choice_buttons.clear()
        if self.window is not None:
            self.window.kill()
            self.window = None
