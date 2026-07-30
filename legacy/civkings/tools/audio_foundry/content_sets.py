"""Static content sets: one ambience bed per era + a base SFX library. Pure."""
from __future__ import annotations
from dataclasses import dataclass
from game_data import Era


@dataclass(frozen=True)
class AmbienceBed:
    era: Era
    caption: str   # generation prompt for the ambience engine
    bed_ref: str   # output stem / asset handle


@dataclass(frozen=True)
class SfxDef:
    sfx_id: str
    caption: str   # generation prompt for the SFX engine


ERA_BEDS: dict[Era, AmbienceBed] = {
    Era.ANCIENT:     AmbienceBed(Era.ANCIENT,     "sparse tribal drums, wind over open plains",       "bed_ancient"),
    Era.CLASSICAL:   AmbienceBed(Era.CLASSICAL,   "lyre and marble halls, distant marketplace",       "bed_classical"),
    Era.MEDIEVAL:    AmbienceBed(Era.MEDIEVAL,    "monastic chant, blacksmith and tolling bells",     "bed_medieval"),
    Era.RENAISSANCE: AmbienceBed(Era.RENAISSANCE, "harpsichord and courtly strings, bustling piazza", "bed_renaissance"),
    Era.INDUSTRIAL:  AmbienceBed(Era.INDUSTRIAL,  "steam engines, factory rhythm, brass band",        "bed_industrial"),
    Era.MODERN:      AmbienceBed(Era.MODERN,      "synth pads, city hum and distant traffic",         "bed_modern"),
}

SFX_SET: dict[str, SfxDef] = {
    "battle_clash": SfxDef("battle_clash", "swords and shields clashing in battle"),
    "city_found":   SfxDef("city_found",   "a crowd cheering as a new city is founded"),
    "tech_unlock":  SfxDef("tech_unlock",  "a bright chime marking a discovery"),
    "wonder_built": SfxDef("wonder_built", "triumphant horns for a completed wonder"),
    "era_advance":  SfxDef("era_advance",  "a rising swell as an age turns"),
    "defeat":       SfxDef("defeat",       "a somber toll of loss"),
}


def bed_for(era: Era) -> AmbienceBed:
    return ERA_BEDS[era]
