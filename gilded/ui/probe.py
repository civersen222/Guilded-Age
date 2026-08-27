"""Headless rendering of one full spine screen (mission C4 wave 3).

render_screen(state, screen) drives the SAME draw code the game loop uses:
it switches the view's active tab, clears the accent ledger, and runs the
view's real draw() pass on a fresh surface.  registry.ACCENTS then counts
what the pass recorded in view._accent_log — the probe never guesses.
"""

from __future__ import annotations

import pygame

from gilded.ui.app import DEFAULT_SIZE

_SPINE_TO_TAB = {"House": "House", "Powers": "Powers", "Atlas": "Atlas"}


def render_screen(state, screen: str) -> pygame.Surface:
    """Render one full spine screen for the given app state, headless.

    `screen` is a spine name ("House"/"Powers"/"Atlas"); `state` is the
    app's AppState (state.view is the live BroadsheetView).  Returns the
    freshly drawn surface; state.view._accent_log holds exactly the accent
    marks this pass drew."""
    if screen not in _SPINE_TO_TAB:
        raise ValueError(f"unknown spine {screen!r}")
    view = state.view
    w, h = DEFAULT_SIZE
    surf = pygame.Surface((w, h))
    view.active_tab = _SPINE_TO_TAB[screen]
    # a full spine screen starts at its home page
    if screen == "House":
        view.house_page = "Overview"
    elif screen == "Powers":
        view.powers_page = "Overview"
    view._accent_log = []
    view.draw(surf)
    return surf
