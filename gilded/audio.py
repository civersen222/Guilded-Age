"""Mission C6 - the sound table. Six events, each a real file under
``gilded/assets/audio/`` (licenses recorded in ``LICENSES.md`` there).

``play(event, settings)`` returns True only when a sound actually started.
It returns False when the settings are muted or the mixer is unavailable,
and it NEVER raises - audio must not be able to crash a turn.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import pygame

_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "audio")

SOUND_EVENTS: Dict[str, str] = {
    "ui_press": "ui_press.ogg",
    "end_turn": "end_turn.ogg",
    "war_declared": "war_declared.ogg",
    "beat": "beat.ogg",
    "ending": "ending.ogg",
    "ambient": "ambient.wav",
}

_loaded: Dict[str, pygame.mixer.Sound] = {}


def resolve(event: str) -> str:
    """The absolute path of an event's file."""
    return os.path.join(_AUDIO_DIR, SOUND_EVENTS[event])


def _mixer_ok() -> bool:
    try:
        pygame.mixer.init()
    except (pygame.error, Exception):
        return False
    return True


def play(event: str, settings) -> bool:
    """Play one sound; False when muted or the mixer cannot start."""
    if getattr(settings, "mute", False):
        return False
    path = resolve(event)
    if not os.path.isfile(path):
        return False
    if not _mixer_ok():
        return False
    try:
        snd = _loaded.get(event)
        if snd is None:
            snd = pygame.mixer.Sound(path)
            _loaded[event] = snd
        snd.play()
        return True
    except Exception:
        return False
