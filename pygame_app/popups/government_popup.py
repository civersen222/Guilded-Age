"""Popup — select/change government type for the player's civ."""

from typing import Any, Optional

import pygame
import pygame_gui

from game import GOVERNMENT_TYPES
from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH


WIDTH = 500
HEIGHT = 400
MARGIN = 10
BUTTON_H = 40
BUTTON_W = 120
ROW_H = 55


class GovernmentPopup:
    """Popup showing all government types with bonuses and a switch button."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self._buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._status_label: Optional[pygame_gui.elements.UILabel] = None
        self._game: Any = None
        self._player_civ: str = ""

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game
        self._player_civ = getattr(game.player_civ, "name", "")

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Government",
        )

        current_gov = getattr(game, "governments", {}).get(self._player_civ, "Despotism")

        y = MARGIN + 10
        for gov_name, bonuses in GOVERNMENT_TYPES.items():
            bg = (60, 60, 40) if gov_name == current_gov else (30, 30, 20)
            self.window.set_alphas_to_subordinates(255)

            # bonus description
            bonus_parts = []
            for k, v in bonuses.items():
                sign = "+" if v > 0 else ""
                bonus_parts.append(f"{k}: {sign}{v}")
            bonus_text = ", ".join(bonus_parts) if bonus_parts else "—"

            label_text = f"{gov_name}" + (" (current)" if gov_name == current_gov else "")
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(MARGIN, y, WIDTH - MARGIN * 2, 20),
                text=label_text,
                manager=ui_manager,
                container=self.window,
            )
            label.set_colour([255, 220, 100] if gov_name == current_gov else [200, 200, 200])

            sub_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(MARGIN + 10, y + 18, WIDTH - MARGIN * 2 - 10, 18),
                text=bonus_text,
                manager=ui_manager,
                container=self.window,
            )
            sub_label.set_colour([180, 180, 180])

            # Switch button
            btn_rect = pygame.Rect(WIDTH - BUTTON_W - MARGIN, y + 2, BUTTON_W, BUTTON_H - 4)
            btn = pygame_gui.elements.UIButton(
                relative_rect=btn_rect,
                text="Switch" if gov_name != current_gov else "Active",
                manager=ui_manager,
                container=self.window,
            )
            btn.set_enabled(gov_name != current_gov)
            self._buttons[gov_name] = btn

            y += ROW_H

        # Close button
        close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WIDTH // 2 - 50, HEIGHT - 40, 100, 30),
            text="Close",
            manager=ui_manager,
            container=self.window,
        )
        self._buttons["__close__"] = close_btn

        # Status label
        self._status_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(MARGIN, HEIGHT - 65, WIDTH - MARGIN * 2, 20),
            text="",
            manager=ui_manager,
            container=self.window,
        )
        self._status_label.set_colour([255, 100, 100])

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            gov = event.ui_element.text
            if gov == "Close" or event.ui_element is self._buttons.get("__close__"):
                self._kill()
                return True
            if gov in self._buttons and gov != "__close__":
                self._switch_government(gov)
                return True
        return False

    def _switch_government(self, gov_name: str) -> None:
        game = self._game
        if not game:
            return
        msg = game.change_government(self._player_civ, gov_name)
        if self._status_label:
            self._status_label.set_text(msg)
        # Refresh to update highlights
        self._kill()
        # Re-show via the caller if needed; for simplicity just update status

    def _kill(self) -> None:
        for elem in list(self._buttons.values()):
            elem.kill()
        if self._status_label:
            self._status_label.kill()
            self._status_label = None
        self._buttons.clear()
        if self.window:
            self.window.kill()
            self.window = None
