"""Modal popup — shows a summary of events from the last turn."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

CATEGORY_COLORS: Dict[str, str] = {
    "economy": "#c5a059",
    "combat": "#b23a3a",
    "growth": "#3ab24e",
    "science": "#3a78b2",
    "dynasty": "#8a3ab2",
    "info": "#e0e0e0",
}

CATEGORIZE_HINTS: Dict[str, str] = {
    "gold": "economy",
    "tax": "economy",
    "combat": "combat",
    "attack": "combat",
    "grew": "growth",
    "food": "growth",
    "research": "science",
    "tech": "science",
}


class TurnSummary:
    """Modal popup showing all events from the last turn."""

    WIDTH = 500
    HEIGHT = 400
    MARGIN = 4

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.text_box: Optional[pygame_gui.elements.UITextBox] = None
        self.dismiss_btn: Optional[pygame_gui.elements.UIButton] = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, events: List[str], turn: int) -> None:
        """Show the turn summary popup. If no events, do nothing."""
        if not events:
            return

        # Build HTML text with color-coded events
        parts: List[str] = []
        for event in events:
            color = CATEGORY_COLORS.get(self._detect_category(event), CATEGORY_COLORS["info"])
            parts.append(f"<font color='{color}'>{event}</font><br>")
        html_text = "".join(parts)

        cx = (SCREEN_WIDTH - self.WIDTH) // 2
        cy = (SCREEN_HEIGHT - self.HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, self.WIDTH, self.HEIGHT),
            manager=ui_manager,
            window_display_title=f"Turn {turn} Summary",
        )

        self.text_box = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(
                self.MARGIN,
                self.MARGIN,
                self.WIDTH - self.MARGIN * 2,
                self.HEIGHT - self.MARGIN * 2 - 40,
            ),
            html_text=html_text,
            manager=ui_manager,
            container=self.window,
        )

        self.dismiss_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (self.WIDTH - 100) // 2,
                self.HEIGHT - 40,
                100,
                30,
            ),
            text="Dismiss",
            manager=ui_manager,
            container=self.window,
        )

    def handle_event(self, event) -> bool:
        """If dismiss button pressed, kill the window and return True."""
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and self.dismiss_btn is not None
                and event.ui_element == self.dismiss_btn):
            self._kill()
            return True
        return False

    def _detect_category(self, text: str) -> str:
        """Auto-detect category from keyword hints."""
        lower = text.lower()
        for keyword, cat in CATEGORIZE_HINTS.items():
            if keyword in lower:
                return cat
        return "info"

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        if self.text_box is not None:
            self.text_box.kill()
            self.text_box = None
        if self.dismiss_btn is not None:
            self.dismiss_btn.kill()
            self.dismiss_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
