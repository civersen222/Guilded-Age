"""G21 atlas renderer: boundary trace, picking, and a headless draw."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui.atlas_view import (
    HOUSE_COLORS,
    MINOR_COLOR,
    OCEAN_COLOR,
    FRONT_COLOR,
    draw_atlas,
    pick_province,
    province_panel_lines,
    province_polygons,
)


def _init():
    pygame.init()


def test_palette_shape():
    assert len(HOUSE_COLORS) == 8 and all(len(c) == 3 for c in HOUSE_COLORS)
    for c in (MINOR_COLOR, OCEAN_COLOR, FRONT_COLOR):
        assert len(c) == 3


def test_every_province_traces_a_polygon():
    _init()
    g = GildedGame(seed=42)
    polys = province_polygons(g.atlas)
    assert set(polys) == set(g.atlas.provinces)
    assert all(len(v) >= 3 for v in polys.values())


def test_centroid_picks_its_own_province():
    _init()
    g = GildedGame(seed=42)
    polys = province_polygons(g.atlas)
    hits = 0
    for pid, prov in g.atlas.provinces.items():
        c = prov.center
        if pick_province(g.atlas, polys, (int(c[0] * 8), int(c[1] * 8))) == pid:
            hits += 1
    # Voronoi regions are near-convex; the great majority contain their centroid.
    assert hits >= int(0.9 * len(g.atlas.provinces))


def test_pick_off_map_is_none():
    _init()
    g = GildedGame(seed=42)
    polys = province_polygons(g.atlas)
    assert pick_province(g.atlas, polys, (100000, 100000)) is None


def test_draw_is_headless_safe():
    _init()
    g = GildedGame(seed=42)
    surf = pygame.Surface((1280, 900))
    polys = draw_atlas(surf, g)
    assert set(polys) == set(g.atlas.provinces)


def test_panel_leads_with_the_name():
    _init()
    g = GildedGame(seed=42)
    pid = next(iter(g.atlas.provinces))
    lines = province_panel_lines(g, pid)
    assert any(g.atlas.provinces[pid].name in l for l in lines)

