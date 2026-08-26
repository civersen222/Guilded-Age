"""The UI verb and datum registry.

`VERBS` names every `game.acts` verb in player language: what it does,
why it is available now, and which ladder axis (or ambition) it serves.
`DATA` names the one screen that owns each visible datum, so a number the
player sees always has a home and a face behind it.

Mission C4: the 11 broadsheet tabs are dissolved into three spines —
House, Powers, Atlas. `SCREENS` is the spine order, `GLYPHS` pins which
zoom tier fully draws each map glyph class, `FONTS` ships the two
Banknote typefaces, and `ACCENTS` reports what the renderer actually drew
so the accent law (vermillion = consequence, <= ~5 marks; gold = the
player only) is checkable against real pixels.
"""

from __future__ import annotations

import os

SCREENS = ["House", "Powers", "Atlas"]

GLYPHS = {
    "city": {"tier": "continent"},
    "regiment": {"tier": "region"},
    "battle": {"tier": "region"},
    "strike": {"tier": "parish"},
    "train": {"tier": "parish"},
    "ship": {"tier": "continent"},
    "informant": {"tier": "region"},
}

FONTS = {
    "display": os.path.join("gilded", "assets", "fonts",
                            "BodoniModa[opsz,wght].ttf"),
    "body": os.path.join("gilded", "assets", "fonts", "EBGaramond[wght].ttf"),
}

DATA = {
    "ladder": "Powers",
    "ambition_banner": "House",
    "treasury_journal": "House/Ledger",
    "extraction_dial": "House/Enterprises",
    "beats": "Atlas",
    "unrest": "Atlas",
    "movement": "Atlas",
    "desk": "Atlas",
}

VERBS = {
    "set_dial": {
        "what": "Set an enterprise's extraction dial - how hard you squeeze "
                "your workers",
        "why_now": "The squeeze sets this turn's output, dividends and unrest",
        "serves": "capital",
    },
    "set_ambition": {
        "what": "Set your House's ambition - the Goal the court now backs "
                "or opposes",
        "why_now": "Your stake gives the court a reason to push or pull, "
                   "and pays ladder movement if you fulfil it",
        "serves": "ambition",
    },
    "hold_seat": {
        "what": "Take a seat on an Order's council - the Order's lever "
                "plays in your House's favour: better loan terms, spared "
                "strikes, softer expos\u00e9s",
        "why_now": "The seat changes how each Order's goal lands on your "
                   "House - through the world's own levers, not a grant",
        "serves": "treasury and prestige - the Order's pressure bends "
                  "toward you",
    },
    "informant_on_order": {
        "what": "Place an informant on an Order's council - the Order's "
                "goal family and target are revealed to you",
        "why_now": "Their intentions are unknown until someone sees them",
        "serves": "intelligence - the Order's goal family and target",
    },
    "declare_war": {
        "what": "Declare war on this rival from their dossier - regiments "
                "march, fronts open on the map",
        "why_now": "Their ambitions press on your ladder; a war is the "
                   "harder way to settle it",
        "serves": "standing - the Conquest ladder axis",
    },
    "propose_marriage": {
        "what": "Propose a marriage alliance with this House - ties bind "
                "their ambitions to yours",
        "why_now": "A tie steadies your ladder against their moves",
        "serves": "standing - the prestige ladder axis",
    },
    "place_informant": {
        "what": "Place an informant in this House - their intentions and "
                "agenda become visible to you",
        "why_now": "Their intentions are unknown until someone sees them",
        "serves": "intelligence - the rival's agenda and movements",
    },
}


def _accent_counts(state, screen: str) -> dict:
    """Render the named spine with the real draw code and count the accent
    marks the renderer actually recorded (never a hardcoded guess)."""
    from gilded.ui import probe
    surf = probe.render_screen(state, screen)
    view = state.view
    vermillion = sum(1 for _a in view._accent_log
                     if _a[0] == "vermillion")
    gold_nonplayer = sum(1 for kind, is_player in view._accent_log
                         if kind == "gold" and not is_player)
    return {"vermillion": int(vermillion),
            "gold_nonplayer": int(gold_nonplayer),
            "surface": surf}


def ACCENTS(screen: str, state) -> dict:
    """Count the accent marks the renderer really drew for the named spine
    on this state. Law: vermillion <= 5, gold_nonplayer == 0. The gate
    cross-checks this claim against the actual rendered pixels of
    `probe.render_screen(state, screen)`."""
    return _accent_counts(state, screen)
