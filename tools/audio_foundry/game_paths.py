"""Map foundry content to the paths the game's audio managers load. Pure, no I/O.

MusicManager streams assets/music/<era>.ogg (lowercased era name).
SoundManager walks assets/sounds/<category>/<name>. Foundry SFX are grouped
under the "events" category. Voice narration is pre-baked under assets/audio/voice/.
"""
from __future__ import annotations
from pathlib import Path
from game_data import Era

MUSIC_DIR = Path("assets/music")
SOUNDS_DIR = Path("assets/sounds")
VOICE_DIR = Path("assets/audio/voice")
SFX_CATEGORY = "events"


def era_music_filename(era: Era) -> str:
    """Filename MusicManager expects for an era's ambience bed."""
    return f"{era.name.lower()}.ogg"


def era_music_path(era: Era) -> Path:
    return MUSIC_DIR / era_music_filename(era)


def sfx_target(sfx_id: str, *, ext: str = "wav") -> tuple[str, str, Path]:
    """Return (category, name, path) for an SFX under the game's sounds dir."""
    name = f"{sfx_id}.{ext}"
    return SFX_CATEGORY, name, SOUNDS_DIR / SFX_CATEGORY / name


def voice_path(asset_id: str, *, ext: str = "wav") -> Path:
    """Pre-baked narration clip path for an event/chronicle asset id."""
    return VOICE_DIR / f"{asset_id}.{ext}"