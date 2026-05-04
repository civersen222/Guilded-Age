"""Main Pygame application — the heart of the CivKings GUI."""
import os
import sys
import pygame
import pygame_gui

from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, BG

# Ensure project root is on sys.path so engine imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class GameApp:
    """Main application class — creates the window, runs the loop, manages screens."""

    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        theme_path = os.path.join(os.path.dirname(__file__), 'theme.json')
        self.ui_manager = pygame_gui.UIManager(
            (SCREEN_WIDTH, SCREEN_HEIGHT), theme_path
        )

        self.game = None  # Engine Game instance, set by NewGameDialog
        self.running = True
        self._current_screen = None
        self._screens = {}

        # Import screens lazily to avoid circular imports
        from pygame_app.screens.main_menu import MainMenuScreen
        self._screens['main_menu'] = MainMenuScreen(self)
        self.switch_screen('main_menu')

    def register_screen(self, name: str, screen):
        """Register a screen by name for switching."""
        self._screens[name] = screen

    def switch_screen(self, name: str):
        """Transition to a different screen."""
        if self._current_screen is not None:
            self._current_screen.exit()
        self._current_screen = self._screens[name]
        self._current_screen.enter()

    def handle_resize(self, new_w: int, new_h: int):
        """Handle window resize."""
        self.screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
        self.ui_manager.set_window_resolution((new_w, new_h))

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                self.ui_manager.process_events(event)
                if self._current_screen:
                    self._current_screen.handle_event(event)

            self.ui_manager.update(dt)
            if self._current_screen:
                self._current_screen.update(dt)

            self.screen.fill(BG)
            if self._current_screen:
                self._current_screen.draw(self.screen)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        pygame.quit()


def main():
    app = GameApp()
    app.run()


if __name__ == '__main__':
    main()
