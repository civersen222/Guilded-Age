"""Right sidebar panel — scrollable, color-coded event history."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import (
    RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT, SCREEN_HEIGHT, ACTION_BAR_HEIGHT,
    GOLD,
)

GOLD_TEXT = (197, 160, 89)
WHITE_TEXT = (255, 255, 255)
SUBTLE_TEXT = (136, 136, 136)

CATEGORY_COLORS: Dict[str, tuple] = {
    "economy": GOLD_TEXT,
    "combat": (178, 58, 58),
    "growth": (58, 178, 78),
    "science": (58, 120, 178),
    "dynasty": (138, 58, 178),
    "info": WHITE_TEXT,
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
    MAX_EVENTS = 100

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.rect = rect
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
        )
        self.events: List[str] = []
        self._font = pygame.font.SysFont("consolas", 10)
        self._font_bold = pygame.font.SysFont("consolas", 10, bold=True)
        self._scroll_offset = 0
        self._max_scroll = 0
        self._text_surface: Optional[pygame.Surface] = None

    def add_event(self, text: str, category: str = "info") -> None:
        """Add a single color-coded event to the log."""
        self.events.append((text, category))
        if len(self.events) > self.MAX_EVENTS:
            self.events.pop(0)
        self._update_scroll()
        self._render()

    def add_turn_events(self, events: List[str], turn: int) -> None:
        """Add a batch of events with auto-categorization and a turn separator."""
        self.events.append((f"--- Turn {turn} ---", "separator"))
        for event_text in events:
            category = "info"
            lower = event_text.lower()
            for keyword, cat in CATEGORIZE_HINTS.items():
                if keyword in lower:
                    category = cat
                    break
            self.events.append((event_text, category))
            if len(self.events) > self.MAX_EVENTS:
                self.events.pop(0)
        self._update_scroll()
        self._render()

    def _update_scroll(self) -> None:
        """Update scroll bounds."""
        panel_h = self.rect.height - self.MARGIN * 2
        total_h = len(self.events) * 14 + 20
        self._max_scroll = max(0, total_h - panel_h)

    def _detect_category(self, text: str) -> str:
        """Auto-detect category from keyword hints."""
        lower = text.lower()
        for keyword, cat in CATEGORIZE_HINTS.items():
            if keyword in lower:
                return cat
        return "info"

    def _render(self) -> None:
        """Rebuild the HTML text from stored events."""
        pass  # draw() renders events directly from self.events

    def draw(self, surface: pygame.Surface) -> None:
        """Draw custom event log with polished UI."""
        x = self.panel.get_abs_rect().x
        y = self.panel.get_abs_rect().y
        w = self.panel.get_rect().width
        h = self.panel.get_rect().height

        # Gold border at top
        pygame.draw.line(surface, GOLD_TEXT, (x, y), (x + w, y), 1)

        # Draw events manually for better control
        event_y = y + self.MARGIN - self._scroll_offset
        line_h = 14
        panel_h = h - self.MARGIN * 2

        for event_text, cat in self.events:
            if event_y + line_h < y or event_y > y + panel_h:
                event_y += line_h
                continue

            if cat == "separator":
                color = (102, 102, 102)
            else:
                color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["info"])

            text_surf = self._font.render(event_text[:60], True, color)
            surface.blit(text_surf, (x + 6, event_y))
            event_y += line_h

    def handle_event(self, event) -> Optional[Any]:
        """Handle scroll events for scrolling."""
        if event.type == pygame.MOUSEWHEEL and event.y != 0:
            self._scroll_offset += int(event.y * 30)
            self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll))
            return True
        return None

    def destroy(self) -> None:
        """Kill panel and all child elements."""
        if hasattr(self, "text_box"):
            self.text_box.kill()
        self.panel.kill()
