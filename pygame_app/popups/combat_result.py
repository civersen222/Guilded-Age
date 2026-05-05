"""Popup — battle outcome display."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 400
HEIGHT = 350
MARGIN = 8
BUTTON_H = 30


class CombatResultPopup:
    """Popup showing outcome after combat."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.continue_btn: Optional[pygame_gui.elements.UIButton] = None
        self._result: Any = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, result: Any) -> None:
        """Show the combat result popup."""
        self._result = result

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        victory = getattr(result, "attacker_victory", False) or getattr(result, "defender_victory", False)
        title = "Battle Result"
        if victory:
            title = "Victory!"

        self.window = pygame_gui.elements.UIWindow(
            relative_rect=pygame.Rect(cx, cy, WIDTH, HEIGHT),
            window_title=title,
            manager=ui_manager,
            window_type="modal",
        )

        html = self._build_html(result)
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2 - BUTTON_H),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        self.continue_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WIDTH - 100) // 2, HEIGHT - BUTTON_H - MARGIN, 100, BUTTON_H),
            text="Continue",
            manager=ui_manager,
            container=self.window,
        )

    def _build_html(self, result: Any) -> str:
        """Build HTML content for the combat result."""
        parts: List[str] = []

        # Header
        if getattr(result, "attacker_victory", False):
            parts.append('<h2 style="color: #44cc44;">VICTORY!</h2><br>')
        elif getattr(result, "defender_victory", False):
            parts.append('<h2 style="color: #ff4444;">DEFEAT!</h2><br>')
        else:
            parts.append('<h2>Draw</h2><br>')

        # Description
        desc = getattr(result, "description", "")
        if desc:
            parts.append(f"{desc}<br><br>")

        # Attacker casualties
        att_cas = getattr(result, "attacker_casualties", [])
        if att_cas:
            parts.append(f"<b>Attacker Casualties:</b> {len(att_cas)}<br>")
            for c in att_cas:
                name = getattr(c, "name", "Unknown")
                parts.append(f"• {name}<br>")
        else:
            parts.append("<b>Attacker Casualties:</b> None<br>")

        # Defender casualties
        def_cas = getattr(result, "defender_casualties", [])
        if def_cas:
            parts.append(f"<br><b>Defender Casualties:</b> {len(def_cas)}<br>")
            for c in def_cas:
                name = getattr(c, "name", "Unknown")
                parts.append(f"• {name}<br>")
        else:
            parts.append("<br><b>Defender Casualties:</b> None<br>")

        # XP gained
        att_xp = getattr(result, "attacker_xp", 0)
        def_xp = getattr(result, "defender_xp", 0)
        if att_xp or def_xp:
            parts.append("<br><b>XP Gained:</b><br>")
            if att_xp:
                parts.append(f"Attacker: +{att_xp} XP<br>")
            if def_xp:
                parts.append(f"Defender: +{def_xp} XP<br>")

        return "".join(parts)

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.continue_btn:
                self._kill()
                return True
            return True
        return False

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.info_textbox, self.continue_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.continue_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
