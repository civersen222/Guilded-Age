"""Popup — technology tree display organized by era."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from game_data import TECHNOLOGIES, Era

ERA_ORDER = [Era.ANCIENT, Era.CLASSICAL, Era.MEDIEVAL, Era.RENAISSANCE, Era.INDUSTRIAL, Era.MODERN]
ERA_LABELS = {
    Era.ANCIENT: "Ancient",
    Era.CLASSICAL: "Classical",
    Era.MEDIEVAL: "Medieval",
    Era.RENAISSANCE: "Renaissance",
    Era.INDUSTRIAL: "Industrial",
    Era.MODERN: "Modern",
}
COLOR_DONE = "#44cc44"
COLOR_RESEARCHING = "#4499ff"
COLOR_AVAILABLE = "#cccccc"
COLOR_LOCKED = "#666666"
WIDTH = 900
HEIGHT = 600
MARGIN = 8
BUTTON_H = 30


class TechTreePopup:
    """Popup showing all technologies organized by era."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.research_btn: Optional[pygame_gui.elements.UIButton] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        """Show the technology tree popup."""
        self._game = game

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Technology Tree",
        )

        # Build HTML content
        html = self._build_html(game)
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2 - BUTTON_H),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        # Buttons row
        btn_y = HEIGHT - BUTTON_H - MARGIN
        btn_spacing = 110
        research_x = (WIDTH - btn_spacing * 2 - 20) // 2
        close_x = research_x + btn_spacing + 20

        self.research_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(research_x, btn_y, 100, BUTTON_H),
            text="Research",
            manager=ui_manager,
            container=self.window,
        )
        self.close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(close_x, btn_y, 100, BUTTON_H),
            text="Close",
            manager=ui_manager,
            container=self.window,
        )

    def _build_html(self, game: Any) -> str:
        """Build HTML content for the tech tree display."""
        tech_manager = getattr(game, "tech_manager", None)
        researched = set()
        current_research = None
        available = {}

        if tech_manager:
            researched = set(getattr(tech_manager, "researched", {}))
            current_research = getattr(tech_manager, "current_research", None)
            avail_list = getattr(tech_manager, "get_available_techs", None)
            if callable(avail_list):
                avail = avail_list()
                available = {getattr(t, "name", t): t for t in avail} if avail else {}

        parts: List[str] = []

        for era in ERA_ORDER:
            label = ERA_LABELS[era]
            parts.append(f"<h2>=== {label.upper()} ERA ===</h2><br>")

            era_techs = sorted(
                [t for t in TECHNOLOGIES.values() if t.era == era],
                key=lambda t: t.cost,
            )

            for tech in era_techs:
                name = tech.name
                cost = tech.cost
                prereqs = tech.prerequisites

                if name in researched:
                    parts.append(f'<font color="{COLOR_DONE}">[DONE] {name}</font><br>')
                elif name == current_research:
                    progress = getattr(tech_manager, "current_research_progress", 0)
                    parts.append(
                        f'<font color="{COLOR_RESEARCHING}">'
                        f"[RESEARCHING] {name} ({progress}/{cost})"
                        f"</font><br>"
                    )
                elif name in available:
                    prereq_str = ", ".join(prereqs) if prereqs else "None"
                    parts.append(
                        f'<font color="{COLOR_AVAILABLE}">'
                        f"[AVAILABLE] {name} - Cost: {cost} - Requires: {prereq_str}"
                        f"</font><br>"
                    )
                else:
                    prereq_str = ", ".join(prereqs) if prereqs else "None"
                    parts.append(
                        f'<font color="{COLOR_LOCKED}">'
                        f"[LOCKED] {name} - Requires: {prereq_str}"
                        f"</font><br>"
                    )

            parts.append("<br>")

        return "".join(parts)

    def _refresh(self) -> None:
        """Refresh the popup display."""
        if self.info_textbox is not None and self._game is not None:
            html = self._build_html(self._game)
            self.info_textbox.set_html_text(html)

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_btn:
                self._kill()
                return True
            if event.ui_element == self.research_btn and self._game is not None:
                return self._on_research()
            return True
        return False

    def _on_research(self) -> bool:
        """Start researching the first available tech."""
        tech_manager = getattr(self._game, "tech_manager", None)
        if tech_manager is None:
            return True

        avail_list = getattr(tech_manager, "get_available_techs", None)
        if not callable(avail_list):
            return True

        available = avail_list()
        if not available:
            return True

        # Pick lowest cost available tech
        best = min(available, key=lambda t: getattr(t, "cost", 0))
        tech_name = getattr(best, "name", None) if hasattr(best, "name") else best
        start = getattr(tech_manager, "start_research", None)
        if callable(start):
            start(tech_name)

        self._refresh()
        return True

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.info_textbox, self.research_btn, self.close_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.research_btn = None
        self.close_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
