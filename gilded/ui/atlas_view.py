"""The atlas renderer (mission G21): the map as the player sees it.

Provinces come out of world.py as sets of lattice cells; this module traces
each set's boundary into a screen polygon (marching-squares edge walk), fills
it by its owner's colour, and lays the century's furniture on top - province
names, endowment glyphs, rail as gold dashes, and the live war fronts as red
lines along contested borders. It reads the game; it never changes it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from gilded.world import MINOR_OWNER

# Houses take these in name order; province fill falls back to MINOR_COLOR.
HOUSE_COLORS = [(122, 74, 58), (58, 90, 122), (74, 106, 74), (140, 120, 60),
                (110, 70, 110), (70, 110, 110), (150, 90, 70), (95, 95, 130)]
MINOR_COLOR = (90, 90, 90)
OCEAN_COLOR = (26, 35, 51)
FRONT_COLOR = (208, 64, 64)

BORDER_COLOR = (12, 12, 12)
NAME_COLOR = (232, 226, 210)
GLYPH_COLOR = (250, 240, 200)
RAIL_COLOR = (198, 164, 84)
SELECT_COLOR = (245, 245, 235)

_ENDOWMENT_GLYPH = {"coalfield": "C", "iron": "I", "timber": "T",
                    "farmland": "F", "harbor": "H"}

_font_cache: Dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    f = _font_cache.get(size)
    if f is None:
        if not pygame.font.get_init():
            pygame.font.init()
        f = pygame.font.SysFont("georgia,serif", size)
        _font_cache[size] = f
    return f


# --- boundary tracing --------------------------------------------------------

# A cell (x, y) is the unit square [x, x+1] x [y, y+1]. We emit each exposed
# side as a directed edge, interior kept on a consistent hand, then stitch the
# edges into loops and keep the longest (the outer boundary).
def _boundary_loop(cells: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    filled = set(cells)
    edges: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    def add(p: Tuple[int, int], q: Tuple[int, int]) -> None:
        edges.setdefault(p, []).append(q)

    for (x, y) in cells:
        if (x, y - 1) not in filled:            # top side, walk right
            add((x, y), (x + 1, y))
        if (x + 1, y) not in filled:            # right side, walk down
            add((x + 1, y), (x + 1, y + 1))
        if (x, y + 1) not in filled:            # bottom side, walk left
            add((x + 1, y + 1), (x, y + 1))
        if (x - 1, y) not in filled:            # left side, walk up
            add((x, y + 1), (x, y))

    best: List[Tuple[int, int]] = []
    guard = sum(len(v) for v in edges.values()) + 4
    while edges:
        start = next(iter(edges))
        loop = [start]
        cur = start
        steps = 0
        while steps < guard:
            steps += 1
            outs = edges.get(cur)
            if not outs:
                break
            nxt = outs.pop()
            if not outs:
                del edges[cur]
            if nxt == start:
                break
            loop.append(nxt)
            cur = nxt
        if len(loop) > len(best):
            best = loop
    return _drop_collinear(best)


def _drop_collinear(pts: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if len(pts) < 3:
        return pts
    out: List[Tuple[int, int]] = []
    n = len(pts)
    for i in range(n):
        a = pts[i - 1]
        b = pts[i]
        c = pts[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if cross != 0:
            out.append(b)
    return out if len(out) >= 3 else pts


def province_polygons(atlas, scale: int = 8) -> Dict[int, List[Tuple[int, int]]]:
    """Trace every province's cell set into a scaled screen polygon."""
    polys: Dict[int, List[Tuple[int, int]]] = {}
    for pid, prov in atlas.provinces.items():
        loop = _boundary_loop(prov.cells)
        polys[pid] = [(px * scale, py * scale) for (px, py) in loop]
    return polys


# --- picking -----------------------------------------------------------------

def _point_in_polygon(pos: Tuple[float, float], poly: List[Tuple[int, int]]) -> bool:
    x, y = pos
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and \
                (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def pick_province(atlas, polygons: Dict[int, List[Tuple[int, int]]],
                  pos: Tuple[float, float]) -> Optional[int]:
    """Which province, if any, sits under a screen point."""
    for pid, poly in polygons.items():
        if len(poly) >= 3 and _point_in_polygon(pos, poly):
            return pid
    return None


# --- drawing -----------------------------------------------------------------

def _owner_color(game, owner: str) -> Tuple[int, int, int]:
    if owner == MINOR_OWNER:
        return MINOR_COLOR
    order = sorted(game.houses)
    idx = order.index(owner) if owner in order else 0
    return HOUSE_COLORS[idx % len(HOUSE_COLORS)]


def _dashed_line(surface, color, start, end, dash: int = 8, gap: int = 6,
                 width: int = 2) -> None:
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-6:
        return
    ux, uy = dx / length, dy / length
    step = dash + gap
    d = 0.0
    while d < length:
        sx = x0 + ux * d
        sy = y0 + uy * d
        e = min(d + dash, length)
        ex = x0 + ux * e
        ey = y0 + uy * e
        pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)
        d += step


def draw_atlas(surface, game, selected_pid: Optional[int] = None,
               scale: int = 8) -> Dict[int, List[Tuple[int, int]]]:
    """Paint the whole map onto surface; returns the polygons it used."""
    polys = province_polygons(game.atlas, scale)
    surface.fill(OCEAN_COLOR)

    for pid, prov in game.atlas.provinces.items():
        poly = polys[pid]
        if len(poly) >= 3:
            pygame.draw.polygon(surface, _owner_color(game, prov.owner), poly)
            border = SELECT_COLOR if pid == selected_pid else BORDER_COLOR
            pygame.draw.polygon(surface, border, poly,
                                3 if pid == selected_pid else 1)

    # rail links as gold dashes between province centres
    for (a, b), link in game.atlas.links.items():
        if getattr(link, "rail", False):
            ca = game.atlas.provinces[a].center
            cb = game.atlas.provinces[b].center
            _dashed_line(surface, RAIL_COLOR,
                         (ca[0] * scale, ca[1] * scale),
                         (cb[0] * scale, cb[1] * scale))

    # names and endowment glyphs at each centre
    name_font = _font(14)
    glyph_font = _font(12)
    for pid, prov in game.atlas.provinces.items():
        cx = prov.center[0] * scale
        cy = prov.center[1] * scale
        label = name_font.render(prov.name, True, NAME_COLOR)
        surface.blit(label, (cx - label.get_width() / 2, cy - label.get_height()))
        if prov.endowments:
            glyphs = "".join(_ENDOWMENT_GLYPH.get(k, "?") for k in prov.endowments)
            g = glyph_font.render(glyphs, True, GLYPH_COLOR)
            surface.blit(g, (cx - g.get_width() / 2, cy + 2))

    # live war fronts as red lines along contested borders
    for war in game.wars:
        for front in getattr(war, "fronts", []):
            for (ap, dp) in getattr(front, "border", []):
                if ap in game.atlas.provinces and dp in game.atlas.provinces:
                    ca = game.atlas.provinces[ap].center
                    cd = game.atlas.provinces[dp].center
                    pygame.draw.line(surface, FRONT_COLOR,
                                     (ca[0] * scale, ca[1] * scale),
                                     (cd[0] * scale, cd[1] * scale), 3)
    return polys


def province_panel_lines(game, pid: int) -> List[str]:
    """The click-through ledger for one province."""
    p = game.atlas.provinces[pid]
    owner = "unclaimed" if p.owner == MINOR_OWNER else p.owner
    ends = ", ".join(f"{k} {v}" for k, v in p.endowments.items()) or "none"
    lines = [
        p.name,
        f"owner: {owner}",
        f"terrain: {p.terrain}",
        f"population: {p.population}k   development: {p.development}",
        f"unrest: {p.unrest:.1f}   garrison: {p.garrison}",
        f"endowments: {ends}",
    ]
    return lines

