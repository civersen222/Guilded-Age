"""C8.3 - page transitions: gilded.ui.transitions.frames honours the frame
contract (exactly `steps` frames, deterministic, endpoints within 5% of the
source/destination, the middle frame differs from BOTH ends on >= 5% of
pixels), a tab press records view.last_transition={"kind":"tab", steps>=4},
an End Turn press records {"kind":"end_turn", steps>=4}, and the app loop
plays the frames in order, one per frame clock tick."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pygame

from gilded.ui import app as _app
from gilded.ui.transitions import frames


def _frac_diff(a, b) -> float:
    """Fraction of pixels whose per-channel max distance exceeds 24.
    a and b may be Surfaces or (h, w, 3) arrays."""
    if isinstance(a, pygame.Surface):
        a = np.asarray(pygame.surfarray.pixels3d(a))
    if isinstance(b, pygame.Surface):
        b = np.asarray(pygame.surfarray.pixels3d(b))
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    return float((d > 24).mean())


def _state():
    st = _app.new_app_state(seed=42)
    v = st.view
    v._w, v._h = 1280, 900
    st.screen = pygame.Surface((v._w, v._h))

    class _FakeClock:
        def tick(self, *a, **k):
            return 0

    st.clock = _FakeClock()
    return st, v


def _draw(v, surf):
    v.regions._regions.clear()
    v.last_transition = None
    v.draw(surf)


def test_frames_contract():
    src = pygame.Surface((64, 64))
    src.fill((30, 40, 50))
    dst = pygame.Surface((64, 64))
    dst.fill((200, 100, 30))
    out = frames(src, dst, 8)
    assert len(out) == 8
    assert all(f.get_size() == (64, 64) for f in out)
    assert _frac_diff(out[0], src) < 0.05
    assert _frac_diff(out[-1], dst) < 0.05
    mid = out[len(out) // 2]
    assert _frac_diff(mid, src) >= 0.05
    assert _frac_diff(mid, dst) >= 0.05
    # deterministic: a second run produces identical pixels
    again = frames(src, dst, 8)
    assert _frac_diff(again[4], mid) < 0.01


def test_tab_press_records_transition_and_frames_play_in_order():
    st, v = _state()
    v.tab = "House"
    _draw(v, st.screen)
    tabs = [r for r in v.regions._regions if r.group == "tabs"]
    assert tabs
    tab = next(r for r in tabs
               if r.action.get("tab") is not None and r.action.get("tab") != "House")
    # the press itself records the pending transition
    action = v.handle_click(tab.rect.center)
    assert action == {"tab": tab.action.get("tab")}
    assert v.last_transition is not None
    assert v.last_transition.get("kind") == "tab"
    steps = v.last_transition.get("steps", 0)
    assert steps >= 4
    _app._apply_action(st, action)

    # emulate the press frame: capture the old page, build the frames
    # exactly as step_once does, then let the loop play them one per tick.
    src = st.screen.copy()
    tmp = pygame.Surface(st.screen.get_size())
    tmp.fill((0, 0, 0))
    _draw(v, tmp)
    st._pending_frames = _app.transition_frames(src, tmp, steps)
    st._transition_index = 0
    v.last_transition = None

    seen = []
    for _ in range(steps):
        assert _app.step_once(st) is True
        seen.append(np.asarray(pygame.surfarray.pixels3d(st.screen)).copy())
    # the frames list is exhausted after exactly `steps` ticks
    assert st._pending_frames is None
    assert st._transition_index == 0
    # the first tick showed the old page, the last showed the new page
    assert _frac_diff(seen[0], src) < 0.05
    assert _frac_diff(seen[-1], tmp) < 0.05
    # the middle frame differs from both ends on >= 5% of pixels
    mid = seen[len(seen) // 2]
    assert _frac_diff(mid, src) >= 0.05
    assert _frac_diff(mid, tmp) >= 0.05


def test_end_turn_press_records_transition():
    st, v = _state()
    v.tab = "House"
    _draw(v, st.screen)
    end = next(r for r in v.regions._regions if r.action.get("end_turn"))
    action = v.handle_click(end.rect.center)
    assert action == {"end_turn": True}
    assert v.last_transition is not None
    assert v.last_transition.get("kind") == "end_turn"
    assert v.last_transition.get("steps", 0) >= 4
    v.last_transition = None
