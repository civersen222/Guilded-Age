"""Main menu screen — title, new game, load game, quit."""
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, GOLD, TEXT


class MainMenuScreen(BaseScreen):
    """Title screen with New Game / Load Game / Quit buttons."""

    def __init__(self, app):
        super().__init__(app)
        self.buttons = {}
        self.labels = []

    def enter(self):
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        # Title
        self.labels.append(UILabel(
            relative_rect=pygame.Rect(cx - 300, cy - 200, 600, 60),
            text="CIVKINGS: DYNASTY & DOMINION",
            manager=self.ui_manager,
        ))

        # Subtitle
        self.labels.append(UILabel(
            relative_rect=pygame.Rect(cx - 200, cy - 140, 400, 30),
            text="A Strategy Game of Empires and Bloodlines",
            manager=self.ui_manager,
        ))

        # Buttons
        btn_w, btn_h = 240, 50
        btn_x = cx - btn_w // 2

        self.buttons['new_game'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy - 40, btn_w, btn_h),
            text="New Game",
            manager=self.ui_manager,
        )
        self.buttons['load_game'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy + 30, btn_w, btn_h),
            text="Load Game",
            manager=self.ui_manager,
        )
        self.buttons['quit'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy + 100, btn_w, btn_h),
            text="Quit",
            manager=self.ui_manager,
        )

    def exit(self):
        for btn in self.buttons.values():
            btn.kill()
        for lbl in self.labels:
            lbl.kill()
        self.buttons.clear()
        self.labels.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons.get('quit'):
                self.app.running = False
            elif event.ui_element == self.buttons.get('new_game'):
                self._open_new_game()
            elif event.ui_element == self.buttons.get('load_game'):
                self._load_game()

    def _open_new_game(self):
        from pygame_app.screens.new_game_dialog import NewGameDialog
        if 'new_game_dialog' not in self.app._screens:
            self.app.register_screen('new_game_dialog', NewGameDialog(self.app))
        self.app.switch_screen('new_game_dialog')

    def _load_game(self):
        from pygame_app.screens.load_game_screen import LoadGameScreen
        if 'load_game' not in self.app._screens:
            self.app.register_screen('load_game', LoadGameScreen(self.app))
        self.app.switch_screen('load_game')

    def draw(self, surface):
        pass
