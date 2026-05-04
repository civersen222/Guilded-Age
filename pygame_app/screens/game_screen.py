"""Main gameplay screen — coordinates map, panels, popups."""
import pygame
import pygame_gui
from pygame_gui.elements import UILabel

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, BG, TEXT, GOLD


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, and manages popups."""

    def __init__(self, app):
        super().__init__(app)
        self.elements = []

    def enter(self):
        game = self.app.game
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)

        # Placeholder label showing game is running
        self.elements.append(UILabel(
            relative_rect=pygame.Rect(20, 20, 600, 40),
            text=f"Playing as {civ_name} — Turn {game.state.turn} — Map {game.map.width}x{game.map.height}",
            manager=self.ui_manager,
        ))

        # Placeholder "Next Turn" button
        from pygame_gui.elements import UIButton
        self.next_turn_btn = UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 60, 160, 45),
            text="Next Turn",
            manager=self.ui_manager,
        )
        self.elements.append(self.next_turn_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.next_turn_btn:
                self.app.game.process_turn()
                self._refresh_label()

    def _refresh_label(self):
        """Update the turn label after processing."""
        game = self.app.game
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)
        if self.elements:
            self.elements[0].set_text(
                f"Playing as {civ_name} — Turn {game.state.turn} — Map {game.map.width}x{game.map.height}"
            )

    def draw(self, surface):
        pass
