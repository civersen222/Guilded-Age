"""Popup — city production queue management."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from game_data import BUILDINGS, UNIT_TYPES


class ProductionPopup:
    """Popup for managing a city's production queue."""

    WIDTH = 600
    HEIGHT = 500
    MARGIN = 8
    BUTTON_H = 30
    SEPARATOR_COLOR = "#666666"

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.selection_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.build_btn: Optional[pygame_gui.elements.UIButton] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._city: Any = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, city: Any, game: Any) -> None:
        """Show the production popup for the given city."""
        self._city = city
        self._game = game

        cx = (SCREEN_WIDTH - self.WIDTH) // 2
        cy = (SCREEN_HEIGHT - self.HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, self.WIDTH, self.HEIGHT),
            manager=ui_manager,
            window_display_title=f"Production: {getattr(city, 'name', 'City')}",
        )

        # LEFT side: selection list of available items
        left_w = self.WIDTH // 2 - self.MARGIN
        items = []

        # Units section
        items.append(("-- UNITS --", ""))
        for utype_name, utype in sorted(UNIT_TYPES.items(), key=lambda x: x[1].production_cost):
            items.append((f"{utype.name} ({utype.production_cost} prod)", utype_name))

        # Buildings section
        items.append(("-- BUILDINGS --", ""))
        city_buildings = getattr(city, "buildings", {})
        for bname, btype in sorted(BUILDINGS.items(), key=lambda x: x[1].production_cost):
            if bname not in city_buildings:
                items.append((f"{btype.name} ({btype.production_cost} prod)", bname))

        self.selection_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(
                self.MARGIN, self.MARGIN, left_w, self.HEIGHT - self.MARGIN * 2 - self.BUTTON_H - 10),
            item_list=items,
            manager=ui_manager,
            container=self.window,
        )

        # RIGHT side: info textbox showing current production queue
        right_x = left_w + self.MARGIN * 2
        right_w = self.WIDTH - right_x - self.MARGIN

        html = self._build_queue_html(city)
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(right_x, self.MARGIN, right_w,
                                      self.HEIGHT - self.MARGIN * 2 - self.BUTTON_H - 10),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        # Buttons row
        btn_y = self.HEIGHT - self.BUTTON_H - self.MARGIN
        btn_spacing = 110
        build_x = (self.WIDTH - btn_spacing * 2 - 20) // 2
        close_x = build_x + btn_spacing + 20

        self.build_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(build_x, btn_y, 100, self.BUTTON_H),
            text="Build",
            manager=ui_manager,
            container=self.window,
        )
        self.close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(close_x, btn_y, 100, self.BUTTON_H),
            text="Close",
            manager=ui_manager,
            container=self.window,
        )

    def _build_queue_html(self, city: Any) -> str:
        """Build HTML text for the production queue display."""
        parts = ["<b>Current Production:</b><br>"]

        current = getattr(city, "current_production", None)
        if current:
            cost = city.get_production_cost(current) or 0
            prod = getattr(city, "production", 0)
            progress = min(prod / cost, 1.0) if cost > 0 else 0
            bar_w = int(200 * progress)
            bar = f"[{'#' * bar_w}{'.' * (200 - bar_w)}] {int(progress * 100)}%"
            parts.append(f"{current} — {prod}/{cost} {bar}<br>")
        else:
            parts.append("None<br>")

        parts.append("<br><b>Queue:</b><br>")
        queue = getattr(city, "production_queue", [])
        if queue:
            for item in queue:
                parts.append(f"• {item}<br>")
        else:
            parts.append("Empty<br>")

        rate = getattr(city, "production_capacity", 0)
        parts.append(f"<br><b>Production Rate:</b> {rate}/turn<br>")

        return "".join(parts)

    def _refresh(self) -> None:
        """Refresh the popup display."""
        if self.info_textbox is not None and self._city is not None:
            html = self._build_queue_html(self._city)
            self.info_textbox.html_text = html
            self.info_textbox.rebuild()

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_btn:
                self._kill()
                return True
            if event.ui_element == self.build_btn and self._city is not None:
                return self._on_build()
            return True

        if event.type == pygame_gui.UI_SELECTION_LIST_CHANGED:
            self._refresh()
            return True

        return False

    def _on_build(self) -> bool:
        """Attempt to assign production for the selected item."""
        if self.selection_list is None or self._city is None:
            return True

        selected = self.selection_list.get_selected_item()
        if selected is None:
            return True

        item_id = selected.id
        if not item_id:
            return True

        researched = None
        if self._game and hasattr(self._game, "research"):
            player_name = getattr(self._game.player_civ, "name", "")
            tm = self._game.research.get(player_name)
            if tm:
                researched = getattr(tm, "researched_techs", set())

        owned_res = None
        if self._game and hasattr(self._game, "economy"):
            owned_res = set(getattr(self._game.economy, "resources", {}))

        success = self._city.assign_production(item_id, researched, owned_res)
        if success:
            self._refresh()
        return True

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.selection_list, self.info_textbox, self.build_btn, self.close_btn]:
            if elem is not None:
                elem.kill()
        self.selection_list = None
        self.info_textbox = None
        self.build_btn = None
        self.close_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
