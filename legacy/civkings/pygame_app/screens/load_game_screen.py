"""Load game screen — lists available saves and allows loading."""
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT, SUBTLE, PANEL_BG

from save_system import get_save_slots, load_game


class LoadGameScreen(BaseScreen):
    """Shows available save files and loads the selected one."""

    SAVE_LIST_HEIGHT = 360
    SLOT_H = 80

    def __init__(self, app):
        super().__init__(app)
        self.elements = []
        self.save_buttons = []
        self.save_data = []
        self.scroll_zone = None

    def enter(self):
        cx = SCREEN_WIDTH // 2
        y = 60

        # Title
        title = UILabel(
            relative_rect=pygame.Rect(cx - 200, y, 400, 40),
            text="LOAD GAME",
            manager=self.ui_manager,
        )
        self.elements.append(title)
        y += 50

        # Get available saves
        self.save_data = get_save_slots()

        if not self.save_data:
            lbl = UILabel(
                relative_rect=pygame.Rect(cx - 200, y, 400, 30),
                text="No saves found.",
                manager=self.ui_manager,
            )
            self.elements.append(lbl)
            y += 50

        # Create save slot buttons
        for i, save in enumerate(self.save_data):
            turn = save.get('turn', '?')
            civ = save.get('civilization', 'Unknown')
            ts = save.get('timestamp', 'Unknown')[:19].replace('T', ' ')
            game_over = save.get('game_over', False)
            victory = save.get('victory', '')
            status = f" — {victory}" if game_over and victory else ""

            lbl = UILabel(
                relative_rect=pygame.Rect(cx - 280, y, 260, 25),
                text=f"Turn {turn}  |  {civ}{status}",
                manager=self.ui_manager,
            )
            self.elements.append(lbl)

            date_lbl = UILabel(
                relative_rect=pygame.Rect(cx - 280, y + 25, 260, 20),
                text=ts,
                manager=self.ui_manager,
            )
            self.elements.append(date_lbl)

            btn = UIButton(
                relative_rect=pygame.Rect(cx + 20, y, 120, self.SLOT_H - 5),
                text="Load",
                manager=self.ui_manager,
            )
            self.elements.append(btn)
            self.save_buttons.append((btn, save['file']))
            y += self.SLOT_H

        y += 20

        # Back button
        self.back_btn = UIButton(
            relative_rect=pygame.Rect(cx - 60, y, 120, 45),
            text="Back",
            manager=self.ui_manager,
        )
        self.elements.append(self.back_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()
        self.save_buttons.clear()
        self.save_data.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_btn:
                self.app.switch_screen('main_menu')
            else:
                for btn, filepath in self.save_buttons:
                    if event.ui_element == btn:
                        self._load_save(filepath)
                        return

    def _load_save(self, filepath: str):
        """Load a save file and switch to the game screen."""
        import json
        from game import Game
        try:
            if filepath.endswith('.pkl'):
                game = Game.restore(filepath)
            else:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                game = Game.from_dict(data)
        except Exception as e:
            from pygame_gui.windows import UIMessageWindow
            UIMessageWindow(
                rect=pygame.Rect(400, 300, 350, 100),
                html_message=f"Failed to read save file:<br>{e}",
                manager=self.ui_manager,
                window_type="message_window",
            )
            return

        self.app.game = game

        # Restore AI players
        from ai import AIPlayer
        for civ_name, civ_data in game.civilizations.items():
            if civ_name != game.player_civ.name:
                if civ_name not in game.ai_players:
                    game.ai_players[civ_name] = AIPlayer(civ_name, "standard")

        # Switch to game screen
        from pygame_app.screens.game_screen import GameScreen
        if 'game' not in self.app._screens:
            self.app.register_screen('game', GameScreen(self.app))
        self.app.switch_screen('game')

    def draw(self, surface):
        pass
