"""Dynasty -> voice mapping for narration. Pure, no I/O."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceProfile:
    civ_id: str        # civilization key, e.g. "Rome"
    display_name: str  # human-readable narrator name
    voice_ref: str     # engine voice id / cloned-voice handle


# One voice per playable civilization. voice_ref values are unique handles the
# TTS adapter resolves at build time; display_name is what the chronicle credits.
ROSTER: dict[str, VoiceProfile] = {
    "Rome":        VoiceProfile("Rome",        "The Senate Voice",       "voice_rome"),
    "Greece":      VoiceProfile("Greece",      "The Agora Orator",       "voice_greece"),
    "Mesopotamia": VoiceProfile("Mesopotamia", "The Ziggurat Scribe",    "voice_mesopotamia"),
    "Egypt":       VoiceProfile("Egypt",       "The Nile Herald",        "voice_egypt"),
    "Persia":      VoiceProfile("Persia",      "The Royal Satrap",       "voice_persia"),
    "China":       VoiceProfile("China",       "The Mandate Chronicler", "voice_china"),
    "Mongol":      VoiceProfile("Mongol",      "The Steppe Rider",       "voice_mongol"),
    "Viking":      VoiceProfile("Viking",      "The Saga Skald",         "voice_viking"),
    "India":       VoiceProfile("India",       "The Vedic Sage",         "voice_india"),
    "Byzantium":   VoiceProfile("Byzantium",   "The Purple Court",       "voice_byzantium"),
    "England":     VoiceProfile("England",     "The Crown Herald",       "voice_england"),
    "Ottoman":     VoiceProfile("Ottoman",     "The Sublime Porte",      "voice_ottoman"),
}

_FALLBACK = VoiceProfile("unknown", "The Chronicler", "voice_default")


def profile_for(civ_id: str) -> VoiceProfile:
    """Return the VoiceProfile for a civ, or a neutral fallback narrator."""
    return ROSTER.get(civ_id, _FALLBACK)
