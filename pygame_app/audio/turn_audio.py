"""Per-turn audio orchestration: era music, event narration, and stings.

Managers are injected via AudioBundle so this is testable with fakes and never
needs a display. Every hook is defensive — audio must never crash a turn.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class AudioBundle:
    sound: Any = None          # SoundManager (or fake)
    music: Any = None          # MusicManager (or fake)
    audio: Any = None          # AudioService (or fake)
    play_voice: Optional[Callable[[Path], None]] = None  # plays a narration wav


def _event_to_dict(pending: Any) -> dict:
    """Best-effort adapt a pending CK event to the narrate dict shape."""
    if isinstance(pending, dict):
        return pending
    return {
        "id": getattr(pending, "id", None) or getattr(pending, "event_id", None),
        "title": getattr(pending, "title", "") or getattr(pending, "name", ""),
        "desc": getattr(pending, "desc", "") or getattr(pending, "description", ""),
    }


def _era_name(game: Any) -> Optional[str]:
    civ = getattr(game, "player_civ", None)
    era = getattr(civ, "current_era", None)
    if era is None:
        return None
    return era.name if hasattr(era, "name") else str(era)


def on_turn(game: Any, bundle: AudioBundle) -> None:
    """Drive audio for the just-processed turn. Never raises."""
    try:
        name = _era_name(game)
        if name and bundle.music is not None:
            bundle.music.update_era(name)

        state = getattr(game, "state", None)
        pending = getattr(state, "pending_ck_event", None)
        if pending is not None:
            if bundle.audio is not None:
                path = bundle.audio.narrate_event(_event_to_dict(pending))
                if path is not None and bundle.play_voice is not None:
                    bundle.play_voice(path)
            if bundle.sound is not None:
                bundle.sound.play("events", "era_advance.wav")

        if getattr(state, "game_over", False) and bundle.sound is not None:
            bundle.sound.play("events", "defeat.wav")
    except Exception:
        pass
