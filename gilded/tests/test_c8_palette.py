"""C8.5 — the art pass: at t40 seed 42 the pinned-ink compliance floors.

Gate metric, verbatim: a screen pixel counts as on-ink when it is within
24/channel of one of the 13 pinned inks in gilded/ui/palette.py.
Floors: House >= 0.95, Powers >= 0.95, Atlas >= 0.90.
RIVER stays reserved: zero exact-RIVER pixels anywhere on the Atlas.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

from gilded.ui import palette as P
from gilded.ui.app import new_app_state

INKS = [
    P.rgb(getattr(P, name))
    for name in ("PAPER", "FIELD", "CARD", "INK", "INK2", "DIM", "VERMILLION",
                 "VERMILLION_DARK", "GOLD", "SAGE", "WHEAT", "SLATE", "RIVER")
]
RIVER_RGB = P.rgb(P.RIVER)


def _draw_tab(state, tab):
    view = state.view
    view.tab = tab
    for attr in ("active_tab", "current_tab"):
        if hasattr(view, attr):
            setattr(view, attr, tab)
    view.regions.clear()
    surf = pygame.Surface(state.screen.get_size())
    view.draw(surf)
    W, H = surf.get_size()
    arr = pygame.image.tostring(surf, "RGB")
    return np.frombuffer(arr, dtype=np.uint8).reshape(H, W, 3).astype(np.int16)


def _within_ink(a, tol=24):
    ok = np.zeros(a.shape[:2], dtype=bool)
    for (r, g, b) in INKS:
        ok |= (np.abs(a[:, :, 0] - r) <= tol) & (np.abs(a[:, :, 1] - g) <= tol) \
              & (np.abs(a[:, :, 2] - b) <= tol)
    return ok


def _state_at_t40():
    st = new_app_state(seed=42)
    for _ in range(40):
        st.game.end_turn()
    return st


def test_house_t40_compliance():
    st = _state_at_t40()
    a = _draw_tab(st, "House")
    frac = _within_ink(a).mean()
    assert frac >= 0.95, f"House t40 on-ink fraction {frac:.3f} < 0.95"


def test_powers_t40_compliance():
    st = _state_at_t40()
    a = _draw_tab(st, "Powers")
    frac = _within_ink(a).mean()
    assert frac >= 0.95, f"Powers t40 on-ink fraction {frac:.3f} < 0.95"


def test_atlas_t40_compliance():
    st = _state_at_t40()
    a = _draw_tab(st, "Atlas")
    frac = _within_ink(a).mean()
    assert frac >= 0.90, f"Atlas t40 on-ink fraction {frac:.3f} < 0.90"


def test_river_reserved_on_atlas():
    st = _state_at_t40()
    a = _draw_tab(st, "Atlas")
    river = (a[:, :, 0] == RIVER_RGB[0]) & (a[:, :, 1] == RIVER_RGB[1]) \
            & (a[:, :, 2] == RIVER_RGB[2])
    assert int(river.sum()) == 0, f"Atlas has {int(river.sum())} exact-RIVER pixels"
