"""Runtime voiced path (Mode B). Generate live when possible, else pre-baked.

Live generation enriches the narration line via flavor.author_line when a
Lemonade host is reachable, and always falls back to the pre-baked clip resolved
through game_paths.voice_path. Never raises.
"""
from __future__ import annotations
from pathlib import Path
from .derive import derive_for_event
from .roster import profile_for
from .flavor import author_line
from .adapters import openmoss
from .game_paths import voice_path
from .validate_audio import validate_file
from .lemonade import LemonadeHost


def voice_event(event: dict, cache_dir: Path, *,
                generate: bool = False, dry_run: bool = False,
                fallback: Path | None = None,
                host: LemonadeHost | None = None) -> Path | None:
    """Return an audio path for an event's narration.

    When `generate` is set, enrich the line via the LLM host (if any) and
    synthesize a fresh clip; otherwise, or on any failure, return the pre-baked
    fallback (an explicit `fallback` wins, else game_paths.voice_path). Never raises.
    """
    asset_id = str(event.get("id") or event.get("event_id") or "unknown")
    fb = fallback if fallback is not None else voice_path(asset_id)
    try:
        if generate:
            prompts = derive_for_event(event)
            line = author_line(prompts.tts_line, host=host) or prompts.tts_line
            out = cache_dir / f"{prompts.event_id}.wav"
            openmoss.generate(line, out, dry_run=dry_run)
            ok, _ = validate_file(out)
            if ok:
                return out
    except Exception:
        pass
    if fb is not None and fb.exists():
        return fb
    return None


def voice_chronicle(civ_id: str, text: str, cache_dir: Path, *,
                    generate: bool = False, dry_run: bool = False,
                    fallback: Path | None = None,
                    host: LemonadeHost | None = None) -> Path | None:
    """Voice a chronicle line in a civ's roster voice. Same fallback contract."""
    profile = profile_for(civ_id)
    fb = fallback if fallback is not None else voice_path(f"chronicle_{profile.civ_id}")
    try:
        if generate and text.strip():
            line = author_line(text, host=host) or text
            out = cache_dir / f"chronicle_{profile.civ_id}.wav"
            openmoss.generate(line, out, voice=profile.voice_ref, dry_run=dry_run)
            ok, _ = validate_file(out)
            if ok:
                return out
    except Exception:
        pass
    if fb is not None and fb.exists():
        return fb
    return None