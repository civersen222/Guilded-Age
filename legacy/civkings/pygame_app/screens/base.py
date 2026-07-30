"""Base class for all game screens."""
import pygame
import pygame_gui


class BaseScreen:
    """Abstract base for screens (main menu, game, etc.)."""

    def __init__(self, app):
        self.app = app
        self.ui_manager = app.ui_manager

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass
