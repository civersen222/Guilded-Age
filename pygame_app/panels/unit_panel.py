"""Left sidebar panel — lists all player units with status."""

from typing import Any, Dict, Optional

import pygame
import pygame_gui

from pygame_app.constants import (
    LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT,
    GOLD, GREEN, RED, SUBTLE,
)

GOLD_TEXT = (197, 160, 89)
WHITE_TEXT = (255, 255, 255)
BTN_BG = (30, 32, 40)


class UnitPanel:
    """Left sidebar listing player units."""

    PANEL_HEIGHT = 300
    UNIT_BTN_HEIGHT = 36
    MARGIN = 4

    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.ui_manager = ui_manager
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=ui_manager,
        )
        self.unit_buttons: Dict[pygame_gui.elements.UIButton, Any] = {}
        self._last_unit_keys: tuple = ()
        self._font = pygame.font.SysFont("consolas", 11)
        self._font_bold = pygame.font.SysFont("consolas", 11, bold=True)

    def refresh(self, game: Any) -> None:
        """Rebuild unit buttons only when the unit list actually changes."""
        player_units = [u for u in game.units.values() if u.owner == game.player_civ.name]
        current_keys = tuple((u.unit_type, u.hp, u.max_hp, u.moves_left, str(getattr(u, "position", (0,0)))) for u in player_units)

        if current_keys == self._last_unit_keys:
            return
        self._last_unit_keys = current_keys

        for btn in list(self.unit_buttons.keys()):
            btn.kill()
        self.unit_buttons.clear()

        y = self.MARGIN
        for unit in player_units:
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    self.MARGIN, y,
                    LEFT_PANEL_WIDTH - self.MARGIN * 2,
                    self.UNIT_BTN_HEIGHT,
                ),
                text="",
                manager=self.ui_manager,
                container=self.panel,
            )
            self.unit_buttons[btn] = unit
            y += self.UNIT_BTN_HEIGHT + self.MARGIN

    def draw(self, surface: pygame.Surface) -> None:
        """Draw custom unit panel with polished UI."""
        # Gold border at top
        y_pos = self.panel.get_abs_rect().y
        w = self.panel.get_abs_rect().x + self.panel.get_abs_rect().width
        pygame.draw.line(surface, GOLD_TEXT, (0, y_pos), (w, y_pos), 1)

        for btn, unit in self.unit_buttons.items():
            rect = btn.get_abs_rect().copy()
            rect.x += self.panel.get_abs_rect().x
            rect.y += self.panel.get_abs_rect().y

            # Button background
            pygame.draw.rect(surface, BTN_BG, rect, border_radius=3)

            # Gold accent line on left
            pygame.draw.line(surface, GOLD_TEXT, (rect.x + 2, rect.y + 3),
                             (rect.x + 2, rect.y + rect.height - 3), 2)

            hp = getattr(unit, "hp", 0)
            max_hp = getattr(unit, "max_hp", 0)
            moves = getattr(unit, "moves_left", 0)
            unit_type = getattr(unit, "unit_type", "Unknown")

            # Unit type in gold
            type_surf = self._font_bold.render(unit_type, True, GOLD_TEXT)
            surface.blit(type_surf, (rect.x + 10, rect.y + 3))

            # HP bar background
            bar_w = rect.width - 40
            bar_h = 6
            bar_x = rect.x + 10
            bar_y = rect.y + 20
            pygame.draw.rect(surface, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=2)

            # HP bar fill
            hp_ratio = max(0, hp / max_hp) if max_hp > 0 else 0
            if hp_ratio > 0.5:
                hp_color = GREEN
            elif hp_ratio > 0.25:
                hp_color = GOLD_TEXT
            else:
                hp_color = RED
            pygame.draw.rect(surface, hp_color,
                             (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=2)

            # HP text
            hp_text = f"{hp}/{max_hp}"
            hp_surf = self._font.render(hp_text, True, WHITE_TEXT)
            surface.blit(hp_surf, (bar_x + bar_w - hp_surf.get_width() - 2, bar_y - 1))

            # Moves indicator
            mv_color = GOLD_TEXT if moves > 0 else SUBTLE
            mv_text = f"Mv:{moves}" if moves > 0 else "——"
            mv_surf = self._font.render(mv_text, True, mv_color)
            surface.blit(mv_surf, (rect.x + rect.width - mv_surf.get_width() - 10, rect.y + 3))

    def handle_event(self, event) -> Optional[Any]:
        """If a unit button was pressed, return the unit. Otherwise None."""
        if (event.type == pygame_gui.UI_BUTTON_PRESSED
                and event.ui_element in self.unit_buttons):
            return self.unit_buttons[event.ui_element]
        return None

    def destroy(self) -> None:
        """Kill panel and all child buttons."""
        for btn in self.unit_buttons.keys():
            btn.kill()
        self.unit_buttons.clear()
        self.panel.kill()
