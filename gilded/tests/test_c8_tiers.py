"""C8.1 — atlas zoom tiers: three pressable atlas_zoom regions, three
distinct tier draws (content band differs >= 5% pairwise), and tier
legends that render real words (city/regiment/strike at Parish, capital
at Continent)."""
import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from gilded.ui import app as _app


def _state():
    st = _app.new_app_state(seed=42)
    v = st.view
    v._w, v._h = 1280, 900
    st.screen = pygame.Surface((v._w, v._h))
    return st, v


def _draw(v, screen, tab):
    v.tab = tab
    v.active_tab = tab
    screen.fill((200, 200, 200))
    v.draw(screen)


def test_atlas_registers_three_zoom_regions():
    st, v = _state()
    _draw(v, st.screen, "Atlas")
    zoom = [r for r in v.regions._regions if r.group == "atlas_zoom"]
    assert len(zoom) == 3
    tiers = {list(dict(r.action).items())[0] for r in zoom}
    assert {("zoom", "continent"), ("zoom", "region"), ("zoom", "parish")} == tiers
    for r in zoom:
        assert r.state is r.state.__class__.ENABLED


def test_pressing_zoom_sets_tier():
    st, v = _state()
    _draw(v, st.screen, "Atlas")
    zoom = {r.action["zoom"]: r for r in v.regions._regions
            if r.group == "atlas_zoom"}
    for tier in ("continent", "parish", "region"):
        action = v.handle_click(zoom[tier].rect.center)
        assert action == {"zoom": tier}
        _app._apply_action(st, action)
        assert v.atlas_tier == tier
        # the press itself already set the view tier; the apply must not
        # raise on a view-internal action


def test_tiers_differ_on_the_content_band():
    st, v = _state()
    screen = st.screen
    tiers = ("continent", "region", "parish")
    shots = {}
    for tier in tiers:
        v.atlas_tier = tier
        _draw(v, screen, "Atlas")
        band = screen.subsurface(pygame.Rect(0, 160, v._w, v._h - 200))
        shots[tier] = pygame.surfarray.pixels3d(band).astype(int)
    for i, a in enumerate(tiers):
        for b in tiers[i + 1:]:
            frac = ((shots[a] - shots[b]).max(axis=2) > 24).mean()
            assert frac >= 0.05, f"{a} vs {b}: {frac:.4f}"


def test_tier_legends_render_real_words():
    st, v = _state()
    screen = st.screen
    v.atlas_tier = "parish"
    _draw(v, screen, "Atlas")
    parish_text = [t for (_r, t) in v.text_rows]
    for word in ("city", "regiment", "strike"):
        assert any(word in t for t in parish_text), f"{word} missing at Parish"

    v.atlas_tier = "continent"
    _draw(v, screen, "Atlas")
    cont_text = [t for (_r, t) in v.text_rows]
    assert any("capital" in t for t in cont_text), "capital missing at Continent"
