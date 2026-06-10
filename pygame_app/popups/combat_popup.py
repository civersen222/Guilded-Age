"""Popup — pre-battle combat screen with attacker/defender stats."""

from typing import Any, Optional

import pygame
import pygame_gui

from combat import resolve_combat
from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 420
HEIGHT = 320
MARGIN = 10
BUTTON_H = 32
LABEL_H = 28


class CombatPopup:
    """Popup showing attacker vs defender stats and a Fight button."""

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        attacker: Any,
        defender: Any,
        game: Any,
    ):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.fight_btn: Optional[pygame_gui.elements.UIButton] = None
        self.attacker = attacker
        self.defender = defender
        self.game = game

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=manager,
            window_display_title="Combat",
        )

        # Attacker stats label
        att_text = self._build_stats_text(attacker, "Attacker")
        self.att_label = pygame_gui.elements.UITextBox(
            att_text,
            pygame.Rect(MARGIN, MARGIN, WIDTH - 2 * MARGIN, LABEL_H),
            container=self.window,
        )

        # Defender stats label
        def_text = self._build_stats_text(defender, "Defender")
        self.def_label = pygame_gui.elements.UITextBox(
            def_text,
            pygame.Rect(MARGIN, MARGIN + 30, WIDTH - 2 * MARGIN, LABEL_H),
            container=self.window,
        )

        # Fight button
        btn_w = 120
        btn_h = BUTTON_H
        btn_x = (WIDTH - btn_w) // 2
        btn_y = HEIGHT - MARGIN - btn_h
        self.fight_btn = pygame_gui.elements.UIButton(
            text="Fight!",
            relative_rect=pygame.Rect(btn_x, btn_y, btn_w, btn_h),
            container=self.window,
        )

    @staticmethod
    def _build_stats_text(unit: Any, role: str) -> str:
        """Build an HTML stats string for a unit/faction."""
        name = getattr(unit, "name", role)
        atk = getattr(unit, "attack", "?")
        _def = getattr(unit, "defense", "?")
        hp = getattr(unit, "hp", "?")
        return (
            f"<b>{role}:</b> {name} | "
            f"Atk: {atk} | Def: {_def} | HP: {hp}"
        )

    def _kill(self) -> None:
        self.hide()

    def handle_event(self, event: pygame.event.Event) -> Optional[Any]:
        """Return a CombatResult when Fight is pressed, else None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.fight_btn:
            return self._resolve()
        return None

    def _resolve(self) -> Any:
        """Call resolve_combat and hide the popup."""
        result = resolve_combat(
            attacker_army=getattr(self.attacker, "army", [self.attacker]),
            defender_army=getattr(self.defender, "army", [self.defender]),
            tile=getattr(self.game, "selected_tile", None),
            attacker_ruler=getattr(self.attacker, "ruler", self.attacker),
            defender_ruler=getattr(self.defender, "ruler", self.defender),
        )
        self.hide()
        return result

    def hide(self):
        """Kill all child elements and the window."""
        for elem in [self.att_label, self.def_label, self.fight_btn]:
            if elem is not None:
                elem.kill()
        self.att_label = None
        self.def_label = None
        self.fight_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
