"""C8.2 - engraved portraits on the court cards: >= 6 pressable portrait
regions on the House tab at t0 (seed 42), each rect >= 48x48, real distinct
engravings blitted inside (pairwise crop difference >= 0.10), identical on
redraw, and the licensed pool on disk (>= 24 images + LICENSES.md)."""

import os
import sys
from itertools import combinations

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gilded.ui import app as _app
from gilded.ui import portraits as P

_POOL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "portraits")


def _state():
    st = _app.new_app_state(seed=42)
    v = st.view
    v._w, v._h = 1280, 900
    v.tab = "House"
    return st, v


def _draw(v):
    v.regions._regions.clear()
    surf = pygame.Surface((v._w, v._h))
    v.draw(surf)
    return surf


def test_six_portrait_regions_on_house_t0():
    st, v = _state()
    surf = _draw(v)
    ports = [r for r in v.regions._regions if r.group == "portrait"]
    assert len(ports) >= 6
    for r in ports:
        assert r.rect.w >= 48 and r.rect.h >= 48, r.rect
        assert r.action.get("portrait"), r.action
    # each portrait sits on a court card: a court_seats region overlaps it
    cards = [c.rect for c in v.regions._regions if c.group == "court_seats"]
    for r in ports:
        assert any(c.collidepoint(r.rect.center) for c in cards), r.rect


def test_portrait_crops_distinct_and_stable():
    st, v = _state()
    s1 = _draw(v)
    s2 = _draw(v)
    ports = [r for r in v.regions._regions if r.group == "portrait"]
    crops1 = [s1.subsurface(r.rect) for r in ports]
    crops2 = [s2.subsurface(r.rect) for r in ports]
    for a, b in combinations(range(len(ports)), 2):
        ca = pygame.image.tobytes(crops1[a], "RGB")
        cb = pygame.image.tobytes(crops1[b], "RGB")
        diff = sum(1 for x, y in zip(ca, cb) if abs(x - y) > 24) / len(ca)
        assert diff >= 0.10, (a, b, diff)
    for a, b in zip(crops1, crops2):
        assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b, "RGB")


def test_portrait_pool_licensed():
    imgs = [f for f in os.listdir(_POOL_DIR)
            if f.lower().endswith((".jpg", ".png", ".flac")) and not f.startswith("LICENSE")]
    assert len(imgs) >= 24, len(imgs)
    assert os.path.isfile(os.path.join(_POOL_DIR, "LICENSES.md"))


def test_portrait_for_deterministic_and_sex_pooled():
    class C:
        def __init__(self, cid, gender):
            self.id = cid
            self.name = "x"
            self.gender = gender
    m = C("111", "Male")
    f = C("222", "Female")
    assert P.portrait_for(m) == P.portrait_for(C("111", "Male"))
    assert os.path.basename(P.portrait_for(m)).startswith("man_")
    assert os.path.basename(P.portrait_for(f)).startswith("woman_")
    # stable per id: different ids land on different files
    assert P.portrait_for(C("111", "Male")) != P.portrait_for(C("112", "Male"))
    assert os.path.isfile(P.portrait_for(m))
