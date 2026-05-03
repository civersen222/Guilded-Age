"""Sound effects system for game events."""

import random
import os
from typing import Dict, Optional


class SoundEffects:
    """Manages game sound effects using system sounds."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.volume: float = 0.5
        self._loaded_sounds: Dict[str, any] = {}
    
    def play(self, sound_name: str) -> bool:
        """Play a named sound effect."""
        if not self.enabled:
            return False
        
        if sound_name not in self._loaded_sounds:
            self._loaded_sounds[sound_name] = self._load_sound(sound_name)
        
        sound = self._loaded_sounds[sound_name]
        if sound is None:
            return False
        
        return self._play_sound(sound)
    
    def _load_sound(self, sound_name: str) -> Optional[any]:
        """Load a sound effect by name."""
        # Try to find sound file
        sound_paths = [
            f"sounds/{sound_name}.wav",
            f"assets/sounds/{sound_name}.wav",
        ]
        
        for path in sound_paths:
            if os.path.exists(path):
                try:
                    import winsound
                    winsound.PlaySound(path, winsound.SND_FILENAME)
                    return path
                except Exception:
                    continue
        
        # Fallback: use system sound
        return self._get_system_sound(sound_name)
    
    def _get_system_sound(self, sound_name: str) -> Optional[str]:
        """Get system sound for a game event."""
        system_sounds = {
            "combat": "SystemExclamation",
            "victory": "SystemAsterisk",
            "defeat": "SystemHand",
            "build_complete": "SystemExclamation",
            "tech_researched": "SystemAsterisk",
            "diplomacy": "SystemQuestion",
            "error": "SystemExclamation",
        }
        return system_sounds.get(sound_name)
    
    def _play_sound(self, sound: any) -> bool:
        """Play a loaded sound."""
        try:
            import winsound
            if isinstance(sound, str) and sound.startswith("System"):
                winsound.PlaySound(
                    getattr(winsound, sound),
                    winsound.SND_ALIAS
                )
            elif isinstance(sound, str):
                winsound.PlaySound(sound, winsound.SND_FILENAME)
            return True
        except Exception:
            return False
    
    def play_combat() -> bool:
        """Play combat sound effect."""
        return self.play("combat")
    
    def play_victory() -> bool:
        """Play victory sound effect."""
        return self.play("victory")
    
    def play_defeat() -> bool:
        """Play defeat sound effect."""
        return self.play("defeat")
    
    def play_build_complete() -> bool:
        """Play build complete sound effect."""
        return self.play("build_complete")
    
    def play_tech_researched() -> bool:
        """Play tech researched sound effect."""
        return self.play("tech_researched")
    
    def play_diplomacy() -> bool:
        """Play diplomacy sound effect."""
        return self.play("diplomacy")


# Global sound manager singleton
_sound_manager: Optional[SoundEffects] = None

def get_sound_manager() -> SoundEffects:
    """Get the global sound manager."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundEffects()
    return _sound_manager
