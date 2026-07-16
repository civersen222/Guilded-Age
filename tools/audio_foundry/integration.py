"""Opt-in Mode B audio service. Flag-off yields pure Mode-A pre-baked assets."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .lemonade import LemonadeHost
from .runtime import voice_event, voice_chronicle


@dataclass
class AudioRuntimeSettings:
    audio_runtime_enabled: bool = False  # Mode B opt-in; default OFF
    cache_dir: Path = field(default_factory=lambda: Path("assets/audio/_cache"))


@dataclass
class AudioService:
    settings: AudioRuntimeSettings = field(default_factory=AudioRuntimeSettings)
    host: LemonadeHost = field(default_factory=LemonadeHost)

    def narrate_event(self, event: dict, *, fallback: Path | None = None,
                      dry_run: bool = False) -> Path | None:
        """Narration audio for an event.

        Flag OFF -> pure Mode-A: return pre-baked `fallback` if present, else None.
        Flag ON  -> try live Mode-B generation, else the same fallback. Never raises.
        """
        return voice_event(
            event, self.settings.cache_dir,
            generate=self.settings.audio_runtime_enabled,
            dry_run=dry_run, fallback=fallback,
        )

    def narrate_chronicle(self, civ_id: str, text: str, *,
                          fallback: Path | None = None,
                          dry_run: bool = False) -> Path | None:
        """Voice a chronicle line. Same flag/fallback contract as narrate_event."""
        return voice_chronicle(
            civ_id, text, self.settings.cache_dir,
            generate=self.settings.audio_runtime_enabled,
            dry_run=dry_run, fallback=fallback,
        )
