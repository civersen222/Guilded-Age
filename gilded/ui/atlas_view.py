"""The atlas renderer (mission G21): the map as the player sees it.

Provinces come out of world.py as sets of lattice cells; this module traces
each set's boundary into a screen polygon (marching-squares edge walk), fills
it by its owner's colour, and lays the century's furniture on top - province
names, endowment glyphs, rail as gold dashes, and the live war fronts as red
lines along contested borders. It reads the game; it never changes it.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Tuple
from collections import namedtuple

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


# --- transform ----------------------------------------------------------------

class AtlasTransform(NamedTuple):
    scale: float
    ox: float
    oy: float

    def apply(self, cell: Tuple[float, float]) -> Tuple[int, int]:
        sx = cell[0] * self.scale + self.ox
        sy = cell[1] * self.scale + self.oy
        return (int(sx), int(sy))


def atlas_transform(atlas, rect: pygame.Rect) -> AtlasTransform:
    """Derive a maximal centred transform that fits the atlas into rect."""
    # Collect all boundary loop vertices to get the true extent
    all_x, all_y = [], []
    for prov in atlas.provinces.values():
        loop = _boundary_loop(prov.cells)
        for px, py in loop:
            all_x.append(px)
            all_y.append(py)
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    lattice_w = max_x - min_x
    lattice_h = max_y - min_y
    if lattice_w == 0:
        lattice_w = 1
    if lattice_h == 0:
        lattice_h = 1
    scale = min(rect.width / lattice_w, rect.height / lattice_h)
    screen_w = scale * lattice_w
    screen_h = scale * lattice_h
    ox = rect.left + (rect.width - screen_w) / 2 - min_x * scale
    oy = rect.top + (rect.height - screen_h) / 2 - min_y * scale
    return AtlasTransform(scale=scale, ox=ox, oy=oy)


def _font(size: int) -> pygame.font.Font:
    f = _font_cache.get(size)
    if f is None:
        if not pygame.font.get_init():
            pygame.font.init()
        f = pygame.font.SysFont("georgia,serif", size)
        _font_cache[size] = f
    return f


# --- legend ------------------------------------------------------------------

LegendRow = namedtuple("LegendRow", ["kind", "label", "color", "glyph"])


def atlas_legend_rows(game) -> List[LegendRow]:
    """One legend entry per colour/glyph that appears on the map."""
    rows: List[LegendRow] = []
    for name in sorted(game.houses):
        rows.append(LegendRow(kind="house", label=name, color=_owner_color(game, name), glyph=""))
    rows.append(LegendRow(kind="unclaimed", label="unclaimed", color=MINOR_COLOR, glyph=""))
    for key in _ENDOWMENT_GLYPH:
        rows.append(LegendRow(kind="endowment", label=key, color=GLYPH_COLOR, glyph=_ENDOWMENT_GLYPH[key]))
    rows.append(LegendRow(kind="rail", label="railway", color=RAIL_COLOR, glyph=""))
    rows.append(LegendRow(kind="front", label="war front", color=FRONT_COLOR, glyph=""))
    return rows


# --- label / glyph layout ----------------------------------------------------

def _rects_collide(a: pygame.Rect, b: pygame.Rect) -> bool:
    return a.colliderect(b)


def atlas_label_rects(game, transform, rect: pygame.Rect,
                      selected_pid=None) -> List[Tuple[int, pygame.Rect]]:
    """Greedy label placement: selected first, then by population desc, name asc."""
    name_font = _font(14)
    # Build ordered list — sort by population desc, name asc, then promote
    # selected_pid to position 0 so the greedy pass tries it first.
    pids = list(game.atlas.provinces.keys())
    pids.sort(key=lambda pid: (
        -(game.atlas.provinces[pid].population),
        game.atlas.provinces[pid].name
    ))
    if selected_pid is not None and selected_pid in game.atlas.provinces:
        pids.remove(selected_pid)
        pids.insert(0, selected_pid)
    drawn: List[Tuple[int, pygame.Rect]] = []
    for pid in pids:
        prov = game.atlas.provinces[pid]
        cx, cy = transform.apply(prov.center)
        label = name_font.render(prov.name, True, NAME_COLOR)
        lr = pygame.Rect(cx - label.get_width() // 2, cy - label.get_height() // 2,
                         label.get_width(), label.get_height())
        # Must be inside content rect
        if not (rect.left <= lr.left and lr.right <= rect.right and
                rect.top <= lr.top and lr.bottom <= rect.bottom):
            continue
        # Must not collide with any already drawn label
        collide = False
        for _, dr in drawn:
            if _rects_collide(lr, dr):
                collide = True
                break
        if not collide:
            drawn.append((pid, lr))
    return drawn


def atlas_glyph_rects(game, transform, rect: pygame.Rect,
                      selected_pid=None) -> List[Tuple[int, pygame.Rect]]:
    """Glyphs only under provinces whose name was drawn, no collisions."""
    glyph_font = _font(12)
    label_rects = atlas_label_rects(game, transform, rect, selected_pid)
    label_pids = {pid for pid, _ in label_rects}
    all_rects = [r for _, r in label_rects]  # label rects to check against
    drawn: List[Tuple[int, pygame.Rect]] = []
    # Same order as labels
    pids = list(game.atlas.provinces.keys())
    pids.sort(key=lambda pid: (
        -(game.atlas.provinces[pid].population),
        game.atlas.provinces[pid].name
    ))
    if selected_pid is not None and selected_pid in game.atlas.provinces:
        pids.remove(selected_pid)
        pids.insert(0, selected_pid)
    for pid in pids:
        if pid not in label_pids:
            continue
        prov = game.atlas.provinces[pid]
        if not prov.endowments:
            continue
        cx, cy = transform.apply(prov.center)
        # Stack glyphs below center
        y_offset = 2
        for endowment in sorted(prov.endowments.keys()):
            g = glyph_font.render(_ENDOWMENT_GLYPH[endowment], True, GLYPH_COLOR)
            gr = pygame.Rect(cx - g.get_width() // 2, cy + y_offset,
                             g.get_width(), g.get_height())
            # Must be inside content rect
            if not (rect.left <= gr.left and gr.right <= rect.right and
                    rect.top <= gr.top and gr.bottom <= rect.bottom):
                continue
            # Must not collide with any label or glyph rect
            collide = False
            for other in all_rects + [r for _, r in drawn]:
                if _rects_collide(gr, other):
                    collide = True
                    break
            if not collide:
                drawn.append((pid, gr))
                all_rects.append(gr)
            y_offset += g.get_height()
    return drawn


# --- boundary tracing --------------------------------------------------------

# A cell (x, y) is the unit square [x, x+1] x [y, y+1]. We emit each exposed
# side as a directed edge, interior kept on a consistent hand, then stitch the
# edges into loops and keep the longest (the outer boundary).
def _boundary_loop(cells: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Trace the outer boundary of a cell set.

    Builds a directed edge graph from cell sides exposed to empty space,
    then stitches edges into a single closed loop.
    """
    filled = set(cells)
    edges: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    def add(p: Tuple[int, int], q: Tuple[int, int]) -> None:
        edges.setdefault(p, []).append(q)

    for (x, y) in filled:
        if (x, y - 1) not in filled:            # top side, walk right
            add((x, y), (x + 1, y))
        if (x + 1, y) not in filled:            # right side, walk down
            add((x + 1, y), (x + 1, y + 1))
        if (x, y + 1) not in filled:            # bottom side, walk left
            add((x + 1, y + 1), (x, y + 1))
        if (x - 1, y) not in filled:            # left side, walk up
            add((x, y + 1), (x, y))

    # Stitch edges into loops — consume edges as we walk
    best: List[Tuple[int, int]] = []
    while edges:
        start = next(iter(edges))
        loop: List[Tuple[int, int]] = [start]
        cur = start
        while True:
            outs = edges.get(cur)
            if outs is None or len(outs) == 0:
                break
            nxt = outs.pop()
            if len(outs) == 0:
                del edges[cur]
            loop.append(nxt)
            if nxt == start:
                break
            cur = nxt
            # Safety valve
            if len(loop) > 10000:
                break
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
    result = out if len(out) >= 3 else pts
    # Re-close the loop if it was open (collinear drop removed the closing vertex)
    if len(result) >= 3 and result[0] != result[-1]:
        result = result + [result[0]]
    return result


def province_polygons(atlas, transform) -> Dict[int, List[Tuple[int, int]]]:
    """Trace every province's cell set into a scaled screen polygon."""
    polys: Dict[int, List[Tuple[int, int]]] = {}
    for pid, prov in atlas.provinces.items():
        loop = _boundary_loop(prov.cells)
        polys[pid] = [transform.apply((px, py)) for (px, py) in loop]
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
        ex = x0 + ux * min(d + dash, length)
        ey = y0 + uy * min(d + dash, length)
        pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)
        d += step


def _draw_legend(surface, game, rect: pygame.Rect) -> pygame.Rect:
    """Draw the legend in the top-left of the content rect. Returns its rect."""
    rows = atlas_legend_rows(game)
    font = _font(12)
    row_h = font.get_height() + 4
    # Two columns layout
    mid = (len(rows) + 1) // 2
    col1 = rows[:mid]
    col2 = rows[mid:]
    # Measure max label width per column
    max_w = 0
    for row in col1:
        if row.kind == "endowment":
            txt = f"{row.glyph} {row.label}"
        else:
            txt = row.label
        w, _ = font.size(txt)
        max_w = max(max_w, w)
    for row in col2:
        if row.kind == "endowment":
            txt = f"{row.glyph} {row.label}"
        else:
            txt = row.label
        w, _ = font.size(txt)
        max_w = max(max_w, w)
    col_w = max_w + 20  # space for color swatch
    legend_w = col_w * 2 + 8
    legend_h = len(col1) * row_h + 8
    # Position in top-left of content rect
    lx = rect.left + 4
    ly = rect.top + 4
    legend_rect = pygame.Rect(lx, ly, legend_w, legend_h)
    # Draw background
    bg = pygame.Surface((legend_w, legend_h))
    bg.set_alpha(200)
    bg.fill((18, 16, 14))
    surface.blit(bg, legend_rect.topleft)
    # Draw rows
    def _draw_col(col_rows, col_x):
        y = col_x + 4  # use col_x as x offset, compute y
        for i, row in enumerate(col_rows):
            ry = ly + 4 + i * row_h
            if row.kind == "endowment":
                txt = f"{row.glyph} {row.label}"
            elif row.kind in ("rail", "front"):
                txt = row.label
                pygame.draw.line(surface, row.color,
                                 (lx + 4, ry + row_h // 2),
                                 (lx + 20, ry + row_h // 2), 3)
            else:
                txt = row.label
                pygame.draw.rect(surface, row.color,
                                 (lx + 4, ry + 2, 14, row_h - 4))
            t = font.render(txt, True, NAME_COLOR)
            surface.blit(t, (lx + 24, ry + 1))
    _draw_col(col1, 0)
    return legend_rect


def draw_atlas(surface, game, rect: pygame.Rect, selected_pid: Optional[int] = None) -> Dict[int, List[Tuple[int, int]]]:
    """Paint the whole map onto surface within rect; returns the polygons it used."""
    transform = atlas_transform(game.atlas, rect)
    polys = province_polygons(game.atlas, transform)

    # Clip all drawing to the content rect
    old_clip = surface.get_clip()
    surface.set_clip(rect)

    try:
        surface.fill(OCEAN_COLOR, rect)

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
                             transform.apply(ca),
                             transform.apply(cb))

        # live war fronts as red lines along contested borders
        for war in game.wars:
            for front in getattr(war, "fronts", []):
                for (ap, dp) in getattr(front, "border", []):
                    if ap in game.atlas.provinces and dp in game.atlas.provinces:
                        ca = game.atlas.provinces[ap].center
                        cd = game.atlas.provinces[dp].center
                        pygame.draw.line(surface, FRONT_COLOR,
                                         transform.apply(ca),
                                         transform.apply(cd), 3)

        # province labels
        labels = atlas_label_rects(game, transform, rect, selected_pid)
        font = _font(12)
        for pid, lr in labels:
            prov = game.atlas.provinces[pid]
            t = font.render(prov.name, True, NAME_COLOR)
            surface.blit(t, lr.topleft)

        # endowment glyphs
        glyphs = atlas_glyph_rects(game, transform, rect, selected_pid)
        glyph_font = _font(11)
        for pid, gr in glyphs:
            prov = game.atlas.provinces[pid]
            for end in prov.endowments:
                char = _ENDOWMENT_GLYPH.get(end, "?")
                t = glyph_font.render(char, True, GLYPH_COLOR)
                surface.blit(t, gr.topleft)

        # legend
        _draw_legend(surface, game, rect)

    finally:
        surface.set_clip(old_clip)

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
