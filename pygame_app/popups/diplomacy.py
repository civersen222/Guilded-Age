"""Popup — diplomatic relations with all known civs."""

from typing import Any, Dict, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH


WIDTH = 700
HEIGHT = 500
MARGIN = 8
BUTTON_H = 30
BUTTON_W = 100
BUTTON_SPACING = 110


class DiplomacyPopup:
    """Popup showing diplomatic relations with all known civs."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.civ_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self._buttons: Dict[str, pygame_gui.elements.UIButton] = {}
        self._game: Any = None
        self._player_civ: str = ""

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        """Show the diplomacy popup."""
        self._game = game
        self._player_civ = getattr(game, "player_civ", None)
        if hasattr(self._player_civ, "name"):
            self._player_civ = self._player_civ.name

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Diplomacy",
        )

        # LEFT: selection list of known civs
        left_w = WIDTH // 2 - MARGIN
        civs = self._get_known_civs()
        items = [(civ, civ) for civ in civs]

        self.civ_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(MARGIN, MARGIN, left_w, HEIGHT - MARGIN * 2 - BUTTON_H - 10),
            item_list=items,
            manager=ui_manager,
            container=self.window,
        )

        # RIGHT: info textbox
        right_x = left_w + MARGIN * 2
        right_w = WIDTH - right_x - MARGIN
        html = self._build_info_html(civs[0] if civs else "")
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(right_x, MARGIN, right_w, HEIGHT - MARGIN * 2 - BUTTON_H - 10),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        # Action buttons row
        btn_y = HEIGHT - BUTTON_H - MARGIN
        actions = [
            ("Declare War", "war"),
            ("Propose Alliance", "alliance"),
            ("Trade Agreement", "trade"),
        ]
        start_x = (WIDTH - BUTTON_SPACING * len(actions) - 10) // 2
        for i, (label, action) in enumerate(actions):
            self._buttons[action] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(start_x + BUTTON_SPACING * i, btn_y, BUTTON_W, BUTTON_H),
                text=label,
                manager=ui_manager,
                container=self.window,
            )

        if civs:
            self._refresh_info(civs[0])

    def _get_known_civs(self) -> List[str]:
        """Get list of known civ names excluding the player."""
        civs = []
        civs_data = getattr(self._game, "civilizations", None)
        if civs_data:
            for name, civ in civs_data.items():
                if name == self._player_civ:
                    continue
                civs.append(name)
        return sorted(civs)

    def _get_status(self, target_civ: str) -> str:
        """Get diplomatic status string for a civ."""
        dm = getattr(self._game, "diplomacy_manager", None)
        if not dm:
            return "Unknown"
        if dm.is_at_war(self._player_civ, target_civ):
            return "At War"
        if dm.is_allied(self._player_civ, target_civ):
            return "Allied"
        score = dm.get_relation(self._player_civ, target_civ)
        if score >= 40:
            return "Friendly"
        if score >= 10:
            return "Neutral"
        if score >= -30:
            return "Unfriendly"
        return "Hostile"

    def _get_active_treaties(self, target_civ: str) -> List[str]:
        """Get list of active treaty names for a civ."""
        dm = getattr(self._game, "diplomacy_manager", None)
        if not dm:
            return []
        treaties = []
        if dm.is_allied(self._player_civ, target_civ):
            treaties.append("Alliance")
        pair = tuple(sorted([self._player_civ, target_civ]))
        truces = getattr(dm, "truces", {})
        if pair in truces:
            treaties.append(f"Truce ({truces[pair]} turns)")
        trade = getattr(dm, "trade_agreements", {})
        if pair in trade:
            treaties.append("Trade Agreement")
        return treaties

    def _build_info_html(self, target_civ: str) -> str:
        """Build HTML info text for a selected civ."""
        if not target_civ:
            return "<i>Select a civilization</i><br>"

        dm = getattr(self._game, "diplomacy_manager", None)
        score = dm.get_relation(self._player_civ, target_civ) if dm else 0
        status = self._get_status(target_civ)
        treaties = self._get_active_treaties(target_civ)

        parts = [f"<b>Relations with {target_civ}:</b> {score}<br>"]
        parts.append(f"<b>Status:</b> {status}<br>")
        parts.append(f"<br><b>Treaties:</b><br>")
        if treaties:
            for t in treaties:
                parts.append(f"• {t}<br>")
        else:
            parts.append("None<br>")

        return "".join(parts)

    def _refresh_info(self, target_civ: str) -> None:
        """Refresh the info textbox for a civ."""
        if self.info_textbox is not None:
            html = self._build_info_html(target_civ)
            self.info_textbox.html_text = html
            self.info_textbox.rebuild()

    def _on_action(self, action: str) -> bool:
        """Execute a diplomatic action."""
        if self.civ_list is None or not self._player_civ:
            return True
        selected = self.civ_list.get_selected_item()
        if not selected:
            return True
        target_civ = selected.id
        if not target_civ:
            return True

        dm = getattr(self._game, "diplomacy_manager", None)
        if not dm:
            return True

        if action == "war":
            dm.declare_war(self._player_civ, target_civ)
        elif action == "alliance":
            dm.propose_alliance(self._player_civ, target_civ)
        elif action == "trade":
            dm.sign_trade_agreement(self._player_civ, target_civ, 5)

        self._refresh_info(target_civ)
        return True

    def handle_event(self, event) -> bool:
        """Handle events from the popup. Returns True if handled."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self._buttons.get("war"):
                return self._on_action("war")
            if event.ui_element == self._buttons.get("alliance"):
                return self._on_action("alliance")
            if event.ui_element == self._buttons.get("trade"):
                return self._on_action("trade")
            # Close button (if added) or any other button kills window
            self._kill()
            return True

        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if self.civ_list is not None:
                selected = self.civ_list.get_selected_item()
                if selected and selected.id:
                    self._refresh_info(selected.id)
            return True

        return False

    def _kill(self) -> None:
        """Kill all child elements and the window."""
        for elem in [self.civ_list, self.info_textbox] + list(self._buttons.values()):
            if elem is not None:
                elem.kill()
        self.civ_list = None
        self.info_textbox = None
        self._buttons.clear()
        if self.window is not None:
            self.window.kill()
            self.window = None
