"""Popup — city production queue management."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from game_data import BUILDINGS, UNIT_TYPES
from game import Game, WORLD_WONDERS


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

        # Get buildable items from city
        researched_techs = None
        owned_resources = None
        if self._game and hasattr(self._game, "tech_manager"):
            tm = self._game.tech_manager
            researched_techs = set(getattr(tm, "unlocked_techs", {}).keys())
        if self._game and hasattr(self._game, "economy"):
            owned_resources = set(getattr(self._game.economy, "resources", {}).keys())

        buildable_units = city.get_buildable_units(researched_techs=researched_techs, owned_resources=owned_resources)
        buildable_buildings = city.get_buildable_buildings(researched_techs=researched_techs)

        # Units section
        items.append(("-- UNITS --", ""))
        for utype_name in sorted(buildable_units, key=lambda n: UNIT_TYPES[n].production_cost):
            utype = UNIT_TYPES[utype_name]
            items.append((f"{utype.name} ({utype.production_cost} prod)", utype_name))

        # Buildings section
        items.append(("-- BUILDINGS --", ""))
        for bname in sorted(buildable_buildings, key=lambda n: BUILDINGS[n].production_cost):
            btype = BUILDINGS[bname]
            items.append((f"{btype.name} ({btype.production_cost} prod)", bname))

        # Wonders section
        items.append(("-- WONDERS --", ""))
        wonders_built = set(getattr(self._game, "wonders_built", {}).keys())
        for wname in sorted(WORLD_WONDERS, key=lambda n: WORLD_WONDERS[n]["cost"]):
            if wname not in wonders_built:
                w = WORLD_WONDERS[wname]
                bonus_descs = []
                for k, v in w.items():
                    if k == "cost":
                        continue
                    bonus_descs.append(f"{k}: +{v}")
                bonus_str = ", ".join(bonus_descs) if bonus_descs else "no bonus"
                items.append((f"{wname} ({w['cost']} gold) — {bonus_str}", f"wonder:{wname}"))

        self._id_by_label = {label: pid for label, pid in items}

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

        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            self._refresh()
            return True

        return False

    def _on_build(self) -> bool:
        """Attempt to assign production for the selected item."""
        if self.selection_list is None or self._city is None:
            return True

        label = self.selection_list.get_single_selection()
        if label is None:
            return True

        item_id = getattr(self, "_id_by_label", {}).get(label, "")
        if not item_id:
            return True

        researched = None
        if self._game and hasattr(self._game, "tech_manager"):
            tm = self._game.tech_manager
            researched = set(getattr(tm, "researched", {}).keys())

        owned_res = None
        if self._game and hasattr(self._game, "economy"):
            owned_res = set(getattr(self._game.economy, "resources", {}).keys())

        if item_id.startswith("wonder:"):
            wonder_name = item_id[len("wonder:"):]
            civ_name = self._game.player_civ.name if hasattr(self._game, "player_civ") else None
            if not civ_name:
                civ_name = self._city.owner.name if self._city.owner else "Player"
            result = self._game.build_wonder(civ_name, wonder_name)
            if self.info_textbox is not None:
                if "needs" in result.lower() or "already" in result.lower():
                    self.info_textbox.html_text = f"[red]{result}[/red]" + self.info_textbox.html_text
                else:
                    self.info_textbox.html_text = f"[green]{result}[/green]" + self.info_textbox.html_text
                self.info_textbox.rebuild()
            return True

        success = self._city.assign_production(item_id, researched_techs=researched, owned_resources=owned_res)
        if success:
            self._refresh()
            if self.info_textbox is not None:
                self.info_textbox.html_text = f"[green]Building [bold]{item_id}[/bold]![/green]" + self.info_textbox.html_text
                self.info_textbox.rebuild()
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
