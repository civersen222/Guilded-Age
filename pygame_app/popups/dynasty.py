"""Popup — dynasty ruler, heirs, traits, and court."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 600
HEIGHT = 500
MARGIN = 8
BUTTON_H = 30
STAT_COLORS = {
    "diplomacy": "#4499ff",
    "martial": "#ff4444",
    "stewardship": "#44cc44",
    "intrigue": "#aa44ff",
}


class DynastyPopup:
    """Popup showing current ruler, heirs, traits, and court."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        """Show the dynasty popup."""
        self._game = game

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Dynasty",
        )

        html = self._build_html(game)
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2 - BUTTON_H),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        self.close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WIDTH - 100) // 2, HEIGHT - BUTTON_H - MARGIN, 100, BUTTON_H),
            text="Close",
            manager=ui_manager,
            container=self.window,
        )

    def _build_html(self, game: Any) -> str:
        """Build HTML content for the dynasty popup."""
        parts: List[str] = []

        # Dynasty section
        dynasty = getattr(game, "dynasty", None)
        if dynasty and getattr(dynasty, "root", None):
            ruler = dynasty.root
            parts.append(f"<h2>=== {ruler.name} ===</h2><br>")

            # Age
            parts.append(f"Age: {ruler.age}<br>")

            # Stats
            parts.append("<br><b>Stats:</b><br>")
            for stat in ["diplomacy", "martial", "stewardship", "intrigue"]:
                val = ruler.get_effective_stat(stat)
                color = STAT_COLORS.get(stat, "#cccccc")
                parts.append(f'<font color="{color}">{stat.capitalize()}:</font> {val}<br>')

            # Traits
            parts.append("<br><b>Traits:</b><br>")
            if ruler.traits:
                for trait in ruler.traits:
                    parts.append(f"• {trait}<br>")
            else:
                parts.append("None<br>")

            # Prestige
            prestige = dynasty.calculate_dynastic_prestige()
            parts.append(f"<br><b>Dynasty Prestige:</b> {prestige}<br>")

            # Members / Heirs
            members = dynasty.get_all_members()
            parts.append(f"<br><b>Dynasty Members ({len(members)}):</b><br>")
            for m in members:
                alive = "✓" if m.is_alive else "✗"
                parts.append(f"{alive} {m.name} (Age {m.age})<br>")

        else:
            parts.append("<i>No dynasty established yet.</i><br>")

        # Court section
        court = getattr(game, "court", None)
        if court:
            parts.append("<br><h2>=== Royal Court ===</h2><br>")
            parts.append(f"{court.filled_count}/5 positions filled<br><br>")
            from court import CourtPosition
            for pos in CourtPosition:
                char = court.positions.get(pos)
                if char and char.is_alive:
                    bonus = court.get_bonus(pos)
                    parts.append(f"<b>{pos.value}:</b> {char.name} (+{bonus})<br>")
                else:
                    parts.append(f"<b>{pos.value}:</b> <font color='#888888'>VACANT</font><br>")
        else:
            parts.append("<br><i>No court established.</i><br>")

        return "".join(parts)

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_btn:
                self._kill()
                return True
            return True
        return False

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.info_textbox, self.close_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.close_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
