"""C4 residual (committed): the war panel must not shadow the map field.

With no overlay open, a click on every province centroid resolves to
select_province, and the war verbs remain reachable (their buttons still
hit-test somewhere).
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView, TAB_H, BOTTOM_H, _hud_height
from gilded.ui.atlas_view import atlas_transform


def _content_rect(w, h):
    hud_h = _hud_height()
    return pygame.Rect(0, TAB_H + hud_h, w, h - TAB_H - hud_h - BOTTOM_H)


def _view(seed):
    g = GildedGame(seed=seed)
    v = BroadsheetView(g, next(iter(g.houses)))
    v.active_tab = "Atlas"
    return g, v


def test_rule6_all_centroid_clicks_select_province():
    for seed in (7, 42):
        g, v = _view(seed)
        surf = pygame.Surface((1280, 900))
        v.draw(surf)
        rect = _content_rect(1280, 900)
        transform = atlas_transform(g.atlas, rect)
        for pid, prov in g.atlas.provinces.items():
            pt = transform.apply(prov.center)
            result = v.handle_click(pt)
            assert result == {"select_province": pid}, \
                f"seed {seed} pid {pid}: centroid click gave {result}"


def _toggle_center(v):
    """Center of the war-drawer toggle button, or None."""
    for r in v.regions._regions:
        act = r.action
        if act and "toggle_war_drawer" in act:
            return r.rect.center
    return None


def test_war_toggle_reachable_when_closed():
    """With the drawer closed, the 'War' toggle button hit-tests somewhere."""
    g, v = _view(7)
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pt = _toggle_center(v)
    assert pt is not None, "war toggle button not found in region list"
    v.handle_click(pt)
    assert v.war_drawer is True


def test_war_toggle_reachable_when_open():
    """With the drawer open, the 'Close war' toggle still hit-tests somewhere."""
    g, v = _view(7)
    v.war_drawer = True
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    pt = _toggle_center(v)
    assert pt is not None, "close-war toggle not found while drawer is open"
    v.handle_click(pt)
    assert v.war_drawer is False


def test_war_drawer_does_not_shadow_centroids():
    """The open war drawer rect must not contain any province centroid."""
    g, v = _view(7)
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    content = _content_rect(1280, 900)
    drawer = v._war_drawer_rect(content)
    transform = atlas_transform(g.atlas, content)
    shadowed = []
    for pid, prov in g.atlas.provinces.items():
        pt = transform.apply(prov.center)
        if drawer.collidepoint(pt):
            shadowed.append(pid)
    assert not shadowed, f"war drawer shadows centroids of {shadowed[:10]}"
