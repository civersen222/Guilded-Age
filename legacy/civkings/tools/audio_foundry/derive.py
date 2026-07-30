"""Derive TTS lines and SFX captions from event content. Pure, no I/O."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioPrompts:
    event_id: str
    tts_line: str      # narration text spoken aloud
    sfx_caption: str   # short caption describing the event's sound


def derive_for_event(event: dict) -> AudioPrompts:
    eid = str(event.get("id") or event.get("event_id") or "unknown")
    title = (event.get("title") or "").strip()
    desc = (event.get("desc") or event.get("description") or "").strip()
    tts_line = f"{title}. {desc}".strip(". ").strip() or title or eid
    sfx_caption = title or desc[:80] or "generic event sting"
    return AudioPrompts(event_id=eid, tts_line=tts_line, sfx_caption=sfx_caption)


def derive_all(events: list[dict]) -> list[AudioPrompts]:
    return [derive_for_event(e) for e in events]