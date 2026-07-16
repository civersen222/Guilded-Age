"""Runtime voiced path (Mode B). Generate live when possible, else pre-baked."""
from __future__ import annotations
from pathlib import Path
from .derive import derive_for_event
from .roster import profile_for
from .adapters import openmoss
from .validate_audio import validate_file


def voice_event(event: dict, cache_dir: Path, *,
                generate: bool = False, dry_run: bool = False,
                fallback: Path | None = None) -> Path | None:
    """Return an audio path for an event's narration.

    If `generate` is set, synthesize a fresh clip into cache_dir via the TTS
    adapter and return it when valid. On any failure (or generate=False) return
    `fallback` if it exists, else None. Never raises.
    """
    try:
        prompts = derive_for_event(event)
        if generate:
            out = cache_dir / f"{prompts.event_id}.wav"
            openmoss.generate(prompts.tts_line, out, dry_run=dry_run)
            ok, _ = validate_file(out)
            if ok:
                return out
    except Exception:
        pass
    if fallback is not None and fallback.exists():
        return fallback
    return None


def voice_chronicle(civ_id: str, text: str, cache_dir: Path, *,
                    generate: bool = False, dry_run: bool = False,
                    fallback: Path | None = None) -> Path | None:
    """Voice a chronicle line in a civ's roster voice. Same fallback contract."""
    try:
        profile = profile_for(civ_id)
        if generate and text.strip():
            out = cache_dir / f"chronicle_{profile.civ_id}.wav"
            openmoss.generate(text, out, voice=profile.voice_ref, dry_run=dry_run)
            ok, _ = validate_file(out)
            if ok:
                return out
    except Exception:
        pass
    if fallback is not None and fallback.exists():
        return fallback
    return None
