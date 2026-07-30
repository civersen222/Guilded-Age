"""Popup — religion display showing faith, founded religions, and followers."""

from typing import Any, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 420
HEIGHT = 350
MARGIN = 10
BUTTON_H = 30


class ReligionPopup:
    """Popup showing faith points and founded religions."""

    def __init__(self, manager: pygame_gui.UIManager, game: Any, player_civ: str):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game = game
        self._player_civ = player_civ

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=manager,
            window_display_title="Religion",
        )

        # Build HTML content
        html = self._build_html()
        self.info_textbox = pygame_gui.elements.UITextBox(
            html,
            pygame.Rect(MARGIN, MARGIN, WIDTH - 2 * MARGIN, HEIGHT - MARGIN - BUTTON_H - 10),
            container=self.window,
        )

        # Close button
        self.close_btn = pygame_gui.elements.UIButton(
            text="Close",
            relative_rect=pygame.Rect(WIDTH // 2 - 40, HEIGHT - MARGIN - BUTTON_H, 80, BUTTON_H),
            object_id="#close",
            container=self.window,
        )

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def _build_html(self) -> str:
        """Build HTML content showing faith and religions."""
        religion_mgr = getattr(self._game, "religion_manager", None)
        economy = getattr(self._game, "economy", None)

        faith = 0
        if economy is not None:
            faith = getattr(economy, "faith", 0)

        lines = [f"<b>Faith Points:</b> {faith}"]

        if religion_mgr is not None:
            religions = getattr(religion_mgr, "religions", {})
            if religions:
                lines.append("<br><b>Founded Religions:</b><br>")
                for name, rel in religions.items():
                    founder = getattr(rel, "founder", "Unknown")
                    total = rel.get_followers_count()
                    lines.append(
                        f"• <b>{name}</b> — Founder: {founder}, Followers: {total}"
                    )
            else:
                lines.append("<br>No religions founded yet.")
        else:
            lines.append("<br>Religion system not available.")

        return "\n".join(lines)

    def _kill(self) -> None:
        self.hide()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle close button click."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.close_btn:
            self.hide()

    def hide(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.info_textbox, self.close_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.close_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
