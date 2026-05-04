"""Right sidebar panel — scrollable, color-coded event history."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT, SCREEN_HEIGHT, ACTION_BAR_HEIGHT

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


class EventLog:
    """Right sidebar with a scrollable, color-coded event log."""

    MARGIN = 4

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
        )
        self.events: List[str] = []

        self.text_box = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(
                self.MARGIN,
                self.MARGIN,
                rect.width - self.MARGIN * 2,
                rect.height - self.MARGIN * 2,
            ),
            html_text="",
            manager=self.ui_manager,
            container=self.panel,
        )

    def add_event(self, text: str, category: str = "info") -> None:
        """Add a single color-coded event to the log."""
        color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["info"])
        self.events.append(text)
        if len(self.events) > 100:
            self.events.pop(0)
        self._render()

    def add_turn_events(self, events: List[str], turn: int) -> None:
        """Add a batch of events with auto-categorization and a turn separator."""
        self.events.append(f"--- Turn {turn} ---")
        for event_text in events:
            category = "info"
            lower = event_text.lower()
            for keyword, cat in CATEGORIZE_HINTS.items():
                if keyword in lower:
                    category = cat
                    break
            self.events.append(event_text)
            if len(self.events) > 100:
                self.events.pop(0)
        self._render()

    def _render(self) -> None:
        """Rebuild the HTML text from stored events."""
        parts: List[str] = []
        for event in self.events:
            if event.startswith("--- Turn ") and event.endswith(" ---"):
                parts.append(f"<font color='#888888'>{event}</font><br>")
            else:
                color = CATEGORY_COLORS.get(self._detect_category(event), CATEGORY_COLORS["info"])
                parts.append(f"<font color='{color}'>{event}</font><br>")
        self.text_box.set_html_text("".join(parts))

    def _detect_category(self, text: str) -> str:
        """Auto-detect category from keyword hints."""
        lower = text.lower()
        for keyword, cat in CATEGORIZE_HINTS.items():
            if keyword in lower:
                return cat
        return "info"

    def destroy(self) -> None:
        """Kill panel and all child elements."""
        self.text_box.kill()
        self.panel.kill()
