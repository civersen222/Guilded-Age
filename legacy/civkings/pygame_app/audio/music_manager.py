"""Music manager — streams era-based background music."""

import os
from typing import Dict

import pygame


class MusicManager:
    """Streams era-based background music."""

    ERA_FILES: Dict[str, str] = {
        "ANCIENT": "ancient.ogg",
        "CLASSICAL": "classical.ogg",
        "MEDIEVAL": "medieval.ogg",
        "RENAISSANCE": "renaissance.ogg",
        "INDUSTRIAL": "industrial.ogg",
        "MODERN": "modern.ogg",
    }

    def __init__(self, music_dir: str = "assets/music"):
        self.music_dir = music_dir
        self.current_era: str = ""
        self.enabled = True

    def update_era(self, era_name: str):
        """Switch to music for the given era."""
        if not self.enabled or era_name == self.current_era:
            return
        filename = self.ERA_FILES.get(era_name.upper())
        if not filename:
            return
        path = os.path.join(self.music_dir, filename)
        if not os.path.isfile(path):
            return
        try:
            pygame.mixer.music.fadeout(2000)
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1, fade_ms=2000)
            self.current_era = era_name.upper()
        except Exception:
            pass

    def stop(self):
        """Stop music playback."""
        pygame.mixer.music.stop()
        self.current_era = ""

    def toggle(self):
        """Toggle enabled state."""
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop()
