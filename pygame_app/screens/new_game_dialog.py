"""New game setup — civilization, difficulty, map size, AI opponents."""
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel, UIDropDownMenu, UIHorizontalSlider

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from game_data import CIVILIZATIONS


class NewGameDialog(BaseScreen):
    """Game setup: pick civ, difficulty, map size, number of AI opponents."""

    def __init__(self, app):
        super().__init__(app)
        self.elements = []
        self.civ_dropdown = None
        self.diff_dropdown = None
        self.map_dropdown = None
        self.ai_count_slider = None
        self.ai_count_label = None
        self.start_btn = None
        self.back_btn = None

    def enter(self):
        cx = SCREEN_WIDTH // 2
        y = 120
        lbl_w, lbl_h = 200, 30
        dd_w, dd_h = 250, 35
        spacing = 60

        # Title
        title = UILabel(
            relative_rect=pygame.Rect(cx - 200, 40, 400, 50),
            text="NEW GAME",
            manager=self.ui_manager,
        )
        self.elements.append(title)

        # Civilization
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Civilization:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        civ_names = sorted(CIVILIZATIONS.keys())
        self.civ_dropdown = UIDropDownMenu(
            options_list=civ_names,
            starting_option=civ_names[0],
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.civ_dropdown)
        y += spacing

        # Difficulty
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Difficulty:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        difficulties = ['Rookie', 'Easy', 'Standard', 'Hard', 'Immortal']
        self.diff_dropdown = UIDropDownMenu(
            options_list=difficulties,
            starting_option='Standard',
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.diff_dropdown)
        y += spacing

        # Map size
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Map Size:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        map_sizes = ['Small (40x40)', 'Medium (56x56)', 'Large (72x72)', 'Huge (96x96)']
        self.map_dropdown = UIDropDownMenu(
            options_list=map_sizes,
            starting_option='Medium (56x56)',
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.map_dropdown)
        y += spacing

        # AI opponents (slider: 1-7)
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="AI Opponents:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        self.ai_count_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(cx - 60, y, 200, lbl_h),
            start_value=3,
            value_range=(1, 7),
            manager=self.ui_manager,
        )
        self.elements.append(self.ai_count_slider)

        self.ai_count_label = UILabel(
            relative_rect=pygame.Rect(cx + 160, y, 60, lbl_h),
            text="3",
            manager=self.ui_manager,
        )
        self.elements.append(self.ai_count_label)
        y += spacing + 40

        # Buttons
        self.start_btn = UIButton(
            relative_rect=pygame.Rect(cx - 140, y, 120, 50),
            text="Start Game",
            manager=self.ui_manager,
        )
        self.elements.append(self.start_btn)

        self.back_btn = UIButton(
            relative_rect=pygame.Rect(cx + 20, y, 120, 50),
            text="Back",
            manager=self.ui_manager,
        )
        self.elements.append(self.back_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_btn:
                self.app.switch_screen('main_menu')
            elif event.ui_element == self.start_btn:
                self._start_game()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.ai_count_slider:
                self.ai_count_label.set_text(str(int(self.ai_count_slider.get_current_value())))

    def _start_game(self):
        """Create engine Game instance and switch to game screen."""
        civ_name = self.civ_dropdown.selected_option[0] if isinstance(
            self.civ_dropdown.selected_option, tuple
        ) else self.civ_dropdown.selected_option
        civ = CIVILIZATIONS[civ_name]
        difficulty = self.diff_dropdown.selected_option
        if isinstance(difficulty, tuple):
            difficulty = difficulty[0]

        # Parse map size
        map_text = self.map_dropdown.selected_option
        if isinstance(map_text, tuple):
            map_text = map_text[0]
        size_map = {
            'Small (40x40)': 40, 'Medium (56x56)': 56,
            'Large (72x72)': 72, 'Huge (96x96)': 96,
        }
        map_size = size_map.get(map_text, 56)

        ai_count = int(self.ai_count_slider.get_current_value())

        # Pick AI civs (exclude player civ)
        from game_data import CIVILIZATIONS as ALL_CIVS
        import random
        all_civ_names = [n for n in ALL_CIVS if n != civ_name]
        if ai_count > 0:
            ai_civ_names = random.sample(all_civ_names, min(ai_count, len(all_civ_names)))
        else:
            ai_civ_names = []
        ai_civs = [ALL_CIVS[name] for name in ai_civ_names]

        # Create game engine with AI civs
        from game import Game
        self.app.game = Game(civ, ai_civs=ai_civs, map_width=map_size, map_height=map_size)

        # Add AI players and their tech managers
        from ai import AIPlayer
        from tech import TechManager
        for ai_name in ai_civ_names:
            self.app.game.ai_players[ai_name] = AIPlayer(ai_name, difficulty.lower())
            self.app.game.research[ai_name] = TechManager()

        # Switch to game screen
        from pygame_app.screens.game_screen import GameScreen
        if 'game' not in self.app._screens:
            self.app.register_screen('game', GameScreen(self.app))
        self.app.switch_screen('game')

    def draw(self, surface):
        pass
