"""Sound effects manager — loads and plays SFX from assets/sounds."""

import os
from typing import Dict, Optional

import pygame


class SoundManager:
    """Loads and plays sound effects."""

    def __init__(self, sounds_dir: str = "assets/sounds"):
        self.sounds_dir = sounds_dir
        self.sounds: Dict[tuple, Optional[pygame.mixer.Sound]] = {}
        self.enabled = True
        self._load_sounds()

    def _load_sounds(self):
        """Walk sounds_dir and load all .ogg/.wav files."""
        if not os.path.isdir(self.sounds_dir):
            return
        for root, _dirs, files in os.walk(self.sounds_dir):
            for fname in files:
                if fname.lower().endswith((".ogg", ".wav")):
                    rel = os.path.relpath(root, self.sounds_dir)
                    category = rel.replace(os.sep, "/") if rel != "." else "default"
                    path = os.path.join(root, fname)
                    try:
                        self.sounds[(category, fname)] = pygame.mixer.Sound(path)
                    except Exception:
                        self.sounds[(category, fname)] = None

    def play(self, category: str, name: str, volume: float = 0.7):
        """Play a sound effect by category and name."""
        if not self.enabled:
            return
        sound = self.sounds.get((category, name))
        if sound is None:
            return
        sound.set_volume(min(volume, 1.0))
        sound.play()

    def toggle(self):
        """Toggle enabled state."""
        self.enabled = not self.enabled
