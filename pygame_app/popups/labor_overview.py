"""Popup — the Squeeze: extraction dials and labor movements (M70, Wave UI)."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from labor import (DIAL_DEFAULT, POP_REF, accident_chance, clamp_dial,
                   dividend_multiplier, production_multiplier, unrest_gain)

WIDTH = 720
HEIGHT = 600
MARGIN = 8
BUTTON_H = 30
LIST_W = 180
DIAL_STEP = 10.0


def _owned_cities(game: Any) -> List[Any]:
    civ = game.player_civ.name
    return [c for c in (getattr(game, "cities", None) or {}).values()
            if c.owner == civ]


def build_labor_html(game: Any) -> str:
    """Every owned city's dial, its arithmetic, and its movement."""
    civ = game.player_civ.name
    parts: List[str] = [
        f"<font size=5><b>=== The Squeeze: labor across House {civ} ===</b></font><br>"]
    tide = getattr(game, "tide", None)
    if tide is not None:
        parts.append(f"<b>Ideological tide:</b> {tide.level:.0f}/100 ({tide.phase()})<br>")
    legit = (getattr(game, "legitimacy", None) or {}).get(civ)
    if legit is not None:
        parts.append(f"<b>Legitimacy:</b> {legit:.0f}/100<br>")
    parts.append("<br>")
    mult = tide.movement_multiplier() if tide is not None else 1.0
    cities = _owned_cities(game)
    if not cities:
        parts.append("<i>The House owns no cities.</i>")
        return "\n".join(parts)
    for city in cities:
        d = getattr(city, "extraction_dial", DIAL_DEFAULT)
        parts.append(f"<b>{city.name}</b> — dial {d:.0f}<br>")
        parts.append(f"&nbsp;&nbsp;production x{production_multiplier(d):.2f}, "
                     f"dividends x{dividend_multiplier(d):.2f}<br>")
        risk = accident_chance(d) * max(0.25, min(2.0, city.population / POP_REF))
        parts.append(f"&nbsp;&nbsp;unrest {city.unrest:.1f} "
                     f"(+{unrest_gain(d) * mult:.2f}/turn), "
                     f"accident risk {risk * 100:.1f}%<br>")
        mv = getattr(city, "movement", None)
        if mv is not None:
            state = "ON STRIKE" if mv.state == "striking" else "unionized"
            who = f" under {mv.leader.name}" if mv.leader is not None else ""
            martyr = f", in {mv.martyr}'s name" if mv.martyr else ""
            parts.append(f'&nbsp;&nbsp;<font color="#ff4444">{state}{who} — '
                         f"militancy {mv.militancy:.0f}{martyr}</font><br>")
        parts.append("<br>")
    return "\n".join(parts)


def adjust_dial(city: Any, delta: float) -> str:
    """Move one city's dial, clamped to the rails."""
    city.extraction_dial = clamp_dial(
        getattr(city, "extraction_dial", DIAL_DEFAULT) + delta)
    return f"{city.name} extraction dial set to {city.extraction_dial:.0f}"


class LaborOverviewPopup:
    """Popup showing the labor overview with dial controls; same contract
    as the other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.city_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.squeeze_btn: Optional[pygame_gui.elements.UIButton] = None
        self.ease_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self._selected_city: Any = None

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game
        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2
        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Labor",
        )
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 3
        self.city_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(MARGIN, MARGIN, LIST_W, content_height),
            item_list=[c.name for c in _owned_cities(game)],
            manager=ui_manager,
            container=self.window,
        )
        self.textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN * 2 + LIST_W, MARGIN,
                                      WIDTH - LIST_W - MARGIN * 3 - 30, content_height),
            html_text=build_labor_html(game),
            manager=ui_manager,
            container=self.window,
        )
        self.squeeze_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Squeeze +10", manager=ui_manager, container=self.window)
        self.ease_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 2 + 150, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Ease -10", manager=ui_manager, container=self.window)

    def handle_event(self, event) -> bool:
        if self._game is None:
            return False
        if (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
                and event.ui_element == self.city_list):
            self._selected_city = next(
                (c for c in _owned_cities(self._game) if c.name == event.text), None)
            return True
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            delta = None
            if event.ui_element == self.squeeze_btn:
                delta = DIAL_STEP
            elif event.ui_element == self.ease_btn:
                delta = -DIAL_STEP
            if delta is not None:
                if self._selected_city is not None:
                    adjust_dial(self._selected_city, delta)
                if self.textbox is not None:
                    self.textbox.set_text(build_labor_html(self._game))
                return True
        return False

    def _kill(self) -> None:
        for elem in [self.city_list, self.textbox, self.squeeze_btn, self.ease_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
