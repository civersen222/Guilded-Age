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
    """Popup showing all technologies organized by era with clickable selection."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.tech_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.details_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.research_btn: Optional[pygame_gui.elements.UIButton] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self._selected_tech_name: Optional[str] = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        """Show the technology tree popup."""
        self._game = game
        self._selected_tech_name = None

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Technology Tree",
        )

        # Top status section — HTML display of all techs (researched/locked)
        status_h = 120
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, status_h),
            html_text=self._build_status_html(game),
            manager=ui_manager,
            container=self.window,
        )

        # LEFT: UISelectionList of available techs
        list_w = WIDTH // 2 - MARGIN * 2
        list_x = MARGIN
        list_y = status_h + MARGIN * 2
        list_h = HEIGHT - list_y - BUTTON_H - MARGIN * 2

        self.tech_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(list_x, list_y, list_w, list_h),
            item_list= [],
            manager=ui_manager,
            container=self.window,
        )

        # RIGHT: UITextBox showing details of selected tech
        details_x = list_x + list_w + MARGIN * 2
        details_y = list_y
        details_w = list_w
        details_h = list_h

        self.details_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(details_x, details_y, details_w, details_h),
            html_text='<font color="#888888">Select a technology to view details</font>',
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

        # Populate the selection list
        self._populate_list(game)

    def _get_tech_status(self, game: Any) -> Dict[str, str]:
        """Return a dict mapping tech name -> status: 'done', 'researching', 'available', 'locked'."""
        tech_manager = getattr(game, "tech_manager", None)
        researched = set()
        current_research = None
        available = set()

        if tech_manager:
            researched = set(getattr(tech_manager, "researched", {}))
            current_research = getattr(tech_manager, "current_research", None)
            avail_list = getattr(tech_manager, "get_available_techs", None)
            if callable(avail_list):
                avail = avail_list()
                available = {getattr(t, "name", t) for t in avail} if avail else set()

        statuses: Dict[str, str] = {}
        for tech in TECHNOLOGIES.values():
            name = tech.name
            if name in researched:
                statuses[name] = "done"
            elif name == current_research:
                statuses[name] = "researching"
            elif name in available:
                statuses[name] = "available"
            else:
                statuses[name] = "locked"
        return statuses

    def _build_status_html(self, game: Any) -> str:
        """Build HTML content for the top status bar (all techs shown compactly)."""
        statuses = self._get_tech_status(game)
        parts: List[str] = []

        for era in ERA_ORDER:
            label = ERA_LABELS[era]
            parts.append(f"<h3>{label.upper()} ERA</h3><br>")

            era_techs = sorted(
                [t for t in TECHNOLOGIES.values() if t.era == era],
                key=lambda t: t.cost,
            )

            for tech in era_techs:
                name = tech.name
                cost = tech.cost
                prereqs = tech.prerequisites
                status = statuses.get(name, "locked")

                if status == "done":
                    parts.append(f'<font color="{COLOR_DONE}">[✓] {name}</font>  ')
                elif status == "researching":
                    progress = getattr(tech_manager, "current_research_progress", 0)
                    parts.append(
                        f'<font color="{COLOR_RESEARCHING}">'
                        f"[RESEARCHING] {name} ({progress}/{cost})"
                        f"</font>  "
                    )
                elif status == "available":
                    prereq_str = ", ".join(prereqs) if prereqs else "None"
                    parts.append(
                        f'<font color="{COLOR_AVAILABLE}">'
                        f"[{name}] ({cost})"
                        f"</font>  "
                    )
                else:
                    prereq_str = ", ".join(prereqs) if prereqs else "None"
                    parts.append(
                        f'<font color="{COLOR_LOCKED}">'
                        f"[{name}] Req: {prereq_str}"
                        f"</font>  "
                    )

            parts.append("<br>")

        return "".join(parts)

    def _populate_list(self, game: Any) -> None:
        """Populate the selection list with available techs."""
        if self.tech_list is None:
            return

        statuses = self._get_tech_status(game)
        # Collect available techs sorted by cost then name
        available_techs = [
            t for t in TECHNOLOGIES.values()
            if statuses.get(t.name) == "available"
        ]
        available_techs.sort(key=lambda t: (t.cost, t.name))

        # Rebuild options (real pygame_gui API: set_item_list)
        self._tech_by_label = {}
        labels = []
        for tech in available_techs:
            label = f"{tech.name} — {tech.cost} gold"
            labels.append(label)
            self._tech_by_label[label] = tech
        self.tech_list.set_item_list(labels)

    def _on_tech_selected(self, tech: Any) -> None:
        """Build and display details for the selected tech."""
        if self.details_textbox is None:
            return

        name = getattr(tech, "name", str(tech))
        cost = getattr(tech, "cost", "?")
        prereqs = getattr(tech, "prerequisites", [])
        effects = getattr(tech, "effects", "")
        era = getattr(tech, "era", None)

        era_label = ERA_LABELS.get(era, str(era)) if era else "Unknown"
        prereq_str = ", ".join(prereqs) if prereqs else "None"

        details_html = f"""
        <b>{name}</b><br>
        <br>
        <b>Era:</b> {era_label}<br>
        <b>Cost:</b> {cost} gold<br>
        <b>Prerequisites:</b> {prereq_str}<br>
        <br>
        <b>Effects:</b><br>
        {effects if effects else "No additional effects listed."}
        """
        self.details_textbox.html_text = details_html
        self.details_textbox.rebuild()

    def _refresh(self) -> None:
        """Refresh the popup display."""
        if self._game is None:
            return
        if self.info_textbox is not None:
            self.info_textbox.html_text = self._build_status_html(self._game)
            self.info_textbox.rebuild()
        if self.tech_list is not None:
            self._populate_list(self._game)

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_btn:
                self._kill()
                return True
            if event.ui_element == self.research_btn and self._game is not None:
                return self._on_research()
            return True
        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.tech_list and event.text:
                tech = getattr(self, "_tech_by_label", {}).get(event.text)
                if tech is not None:
                    self._selected_tech_name = tech.name
                    self._on_tech_selected(tech)
                return True
            return True
        return False

    def _on_research(self) -> bool:
        """Start researching the SELECTED tech."""
        if self._selected_tech_name is None:
            return True

        tech_manager = getattr(self._game, "tech_manager", None)
        if tech_manager is None:
            return True

        start = getattr(tech_manager, "start_research", None)
        if callable(start):
            start(self._selected_tech_name)

        self._refresh()
        return True

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.info_textbox, self.tech_list, self.details_textbox, self.research_btn, self.close_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.tech_list = None
        self.details_textbox = None
        self.research_btn = None
        self.close_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
