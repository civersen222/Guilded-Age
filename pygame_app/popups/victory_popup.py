"""Popup — victory/defeat screen shown when game ends."""

from typing import Any, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 450
HEIGHT = 360
MARGIN = 8
BUTTON_H = 36


class VictoryPopup:
    """Popup showing victory/defeat results."""

    def _kill(self) -> None:
        if self.window is not None:
            self.window.kill()
            self.window = None

    def handle_event(self, event) -> bool:
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.close_btn:
            self._kill()
            return True
        return False

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game

        winner = getattr(game.state, "winner", "Unknown")
        victory_type = getattr(game.state, "victory_type", "Domination")
        turn = getattr(game.state, "turn", 0)
        player_name = getattr(game.player_civ, "name", "") if hasattr(game, "player_civ") else ""
        is_player_win = (winner == player_name)

        title = "VICTORY" if is_player_win else "DEFEAT"
        color = "#44cc44" if is_player_win else "#ff4444"

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title=title,
        )

        # Info text
        stats = getattr(game, "stats", {})
        turns_played = stats.get("turns_played", turn)
        cities_founded = stats.get("cities_founded", 0)
        units_trained = stats.get("units_trained", 0)
        wars_won = stats.get("wars_won", 0)
        techs_researched = stats.get("techs_researched", 0)
        html = f"""
            <p style="font-size:18">Turn: {turn}</p>
            <p style="font-size:22; color:{color}; font-weight:bold">{winner}</p>
            <p style="font-size:16">Victory by: {victory_type}</p>
            <p style="font-size:14">Turns Played: {turns_played}</p>
            <p style="font-size:14">Cities Founded: {cities_founded}</p>
            <p style="font-size:14">Units Trained: {units_trained}</p>
            <p style="font-size:14">Wars Won: {wars_won}</p>
            <p style="font-size:14">Techs Researched: {techs_researched}</p>
        """

        self.info_textbox = pygame_gui.elements.UITextBox(
            html_text=html,
            relative_rect=pygame.Rect(MARGIN, 50, WIDTH - MARGIN * 2, 200),
            container=self.window,
        )

        # Return to menu button
        self.close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WIDTH - 160) // 2, 260, 160, BUTTON_H),
            text="Return to Menu",
            manager=ui_manager,
            container=self.window,
        )

