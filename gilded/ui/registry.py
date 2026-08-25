"""Mission C1 wave 2 - the UI verb and datum registry.

`VERBS` names every `game.acts` verb in player language: what it does,
why it is available now, and which ladder axis (or ambition) it serves.
`DATA` names the one screen that owns each visible datum, so a number the
player sees always has a home and a face behind it.
"""

from __future__ import annotations

VERBS = {
    "set_dial": {
        "what": "Set an enterprise's extraction dial - how hard you squeeze "
                "your workers",
        "why_now": "The squeeze sets this turn's output, dividends and unrest",
        "serves": "capital",
    },
}

DATA = {
    "ladder": "house_tab",
    "treasury_journal": "house_tab",
    "extraction_dial": "house_tab",
    "beats": "broadsheet",
    "unrest": "atlas",
    "movement": "atlas",
}
