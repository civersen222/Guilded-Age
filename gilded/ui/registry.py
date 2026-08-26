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
        "what": "Plant an informant on an Order - its goal becomes visible "
                "in your intel report",
        "why_now": "Orders keep their intentions to themselves; an "
                   "informant reads the Order's current pursuit",
        "serves": "intelligence - the Order's goal family and target",
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
