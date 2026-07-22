"""The Atlas: provinces, links, endowments -- seeded and deterministic (spec section 3).

Generation: seed points -> discrete Voronoi on a lattice -> coastline carve ->
terrain character -> endowments -> road links. Pure stdlib; all randomness flows
from the seed passed to generate_atlas.
"""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

TERRAINS = ("coast", "plains", "highlands", "marsh")
ENDOWMENT_KINDS = ("coalfield", "iron", "timber", "farmland", "harbor")

# --- generation tunables ---
GRID_W, GRID_H = 96, 96
SEED_POINTS = 100
PROVINCE_MIN, PROVINCE_MAX = 50, 70
OCEAN_THRESHOLD = 0.92        # radial falloff + noise beyond this sinks a cell
OCEAN_NOISE = 0.18            # per-region noise weight in the ocean formula
REGION_SINK_FRACTION = 0.50   # regions with less land than this sink entirely
MIN_PROVINCE_CELLS = 6        # slivers below this sink entirely
MAX_ATTEMPTS = 50

MARSH_CHANCE = 0.08
ENDOWMENT_MINIMUMS = {"coalfield": 6, "iron": 6, "farmland": 8, "harbor": 4}
POPULATION_RANGE = {          # thousands of workforce, by terrain
    "plains": (80, 160),
    "coast": (60, 140),
    "highlands": (30, 90),
    "marsh": (20, 50),
}
FARMLAND_POP_BONUS = 1.25

# --- link costs (graph hops weighted by rail, spec section 3) ---
RAIL_HOP_COST, ROAD_HOP_COST = 1.0, 2.0

_ENDOWMENT_WEIGHTS = {
    "coast": (("harbor", 5), ("timber", 2), ("farmland", 2), ("coalfield", 1), ("iron", 1)),
    "plains": (("farmland", 5), ("timber", 2), ("coalfield", 1), ("iron", 1)),
    "highlands": (("coalfield", 4), ("iron", 4), ("timber", 3)),
    "marsh": (("timber", 2), ("farmland", 1)),
}

_NAME_PARTS_A = ["Kar", "Dun", "Vel", "Mor", "Ash", "Bren", "Osten", "Fer", "Gal", "Hol",
                 "Ivar", "Lox", "Nor", "Quill", "Ravn", "Stern", "Thal", "Ulm", "Wick", "Yare"]
_NAME_PARTS_B = ["vess", "more", "wick", "holt", "gard", "mere", "field", "bourne", "stad",
                 "haven", "cliff", "march", "dale", "fen", "burg", "ford", "shore", "moor"]
_NAME_SUFFIXES = ["Vale", "Reach", "Marches", "Head", "Cross"]

MINOR_OWNER = ""


@dataclass
class Province:
    pid: int
    name: str
    terrain: str
    endowments: Dict[str, int]            # kind -> richness 1..3
    cells: List[Tuple[int, int]]          # lattice cells (the UI derives polygons)
    center: Tuple[float, float]
    neighbors: Set[int]
    owner: str = MINOR_OWNER
    population: int = 0                   # workforce pool, thousands
    development: int = 1
    unrest: float = 0.0
    garrison: int = 0
    movement: object = None               # society.labor.Movement, attached later


@dataclass
class Link:
    a: int                                # a < b always
    b: int
    rail: bool = False


class Atlas:
    """Provinces plus the road/rail graph between them."""

    def __init__(self, provinces: Dict[int, Province], links: Dict[Tuple[int, int], Link]):
        self.provinces = provinces
        self.links = links

    def link(self, a: int, b: int) -> Optional[Link]:
        return self.links.get((min(a, b), max(a, b)))

    def neighbors(self, pid: int) -> List[Province]:
        return [self.provinces[n] for n in sorted(self.provinces[pid].neighbors)]

    def distance(self, a: int, b: int) -> float:
        """Dijkstra over links; rail hops are cheaper than road hops."""
        if a == b:
            return 0.0
        dist = {a: 0.0}
        frontier = [(0.0, a)]
        while frontier:
            d, node = heapq.heappop(frontier)
            if node == b:
                return d
            if d > dist.get(node, math.inf):
                continue
            for n in self.provinces[node].neighbors:
                ln = self.link(node, n)
                cost = RAIL_HOP_COST if (ln and ln.rail) else ROAD_HOP_COST
                nd = d + cost
                if nd < dist.get(n, math.inf):
                    dist[n] = nd
                    heapq.heappush(frontier, (nd, n))
        return math.inf


def generate_atlas(seed: int) -> Atlas:
    """Deterministic: the same seed always yields the identical atlas."""
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(seed * 1000 + attempt)
        atlas = _try_generate(rng)
        if atlas is not None:
            return atlas
    raise RuntimeError(f"atlas generation failed for seed {seed}")


def _try_generate(rng: random.Random) -> Optional[Atlas]:
    cells_all = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
    points = rng.sample(cells_all, SEED_POINTS)
    noise = [rng.random() for _ in range(SEED_POINTS)]

    # Discrete Voronoi with a coastline carve: fringe regions sink coherently.
    cx, cy = GRID_W / 2.0, GRID_H / 2.0
    max_radius = min(GRID_W, GRID_H) / 2.0
    region_cells: List[List[Tuple[int, int]]] = [[] for _ in range(SEED_POINTS)]
    region_total = [0] * SEED_POINTS
    for x, y in cells_all:
        best, best_d = 0, math.inf
        for i, (px, py) in enumerate(points):
            d = (px - x) * (px - x) + (py - y) * (py - y)
            if d < best_d:
                best, best_d = i, d
        region_total[best] += 1
        r = math.hypot(x - cx, y - cy) / max_radius
        if r + OCEAN_NOISE * noise[best] > OCEAN_THRESHOLD:
            continue                                  # ocean cell
        region_cells[best].append((x, y))

    landed = [i for i in range(SEED_POINTS)
              if region_total[i] > 0
              and len(region_cells[i]) >= MIN_PROVINCE_CELLS
              and len(region_cells[i]) / region_total[i] >= REGION_SINK_FRACTION]
    if not (PROVINCE_MIN <= len(landed) <= PROVINCE_MAX):
        return None

    # Cell ownership and adjacency; off-grid and carved cells count as ocean.
    landset: Dict[Tuple[int, int], int] = {}
    for i in landed:
        for c in region_cells[i]:
            landset[c] = i
    coastal: Set[int] = set()
    adj: Dict[int, Set[int]] = {i: set() for i in landed}
    for (x, y), i in landset.items():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in landset:
                coastal.add(i)
            else:
                j = landset[n]
                if j != i:
                    adj[i].add(j)
                    adj[j].add(i)

    # Terrain: coast at the sea, highlands deep inland, marsh rare by the shore.
    depth = {i: (0 if i in coastal else math.inf) for i in landed}
    queue = sorted(coastal)
    while queue:
        cur = queue.pop(0)
        for n in sorted(adj[cur]):
            if depth[n] > depth[cur] + 1:
                depth[n] = depth[cur] + 1
                queue.append(n)
    finite = [d for d in depth.values() if d < math.inf] or [0]
    max_depth = max(finite)
    terrain: Dict[int, str] = {}
    for i in landed:
        if i in coastal:
            terrain[i] = "coast"
        elif max_depth >= 2 and depth[i] != math.inf and depth[i] >= max(2, round(max_depth * 2 / 3)):
            terrain[i] = "highlands"
        else:
            terrain[i] = "plains"
    for i in landed:
        if terrain[i] == "plains" and any(terrain[n] == "coast" for n in adj[i]):
            if rng.random() < MARSH_CHANCE:
                terrain[i] = "marsh"

    # Endowments: geography decides what industry is possible where.
    endowments: Dict[int, Dict[str, int]] = {}
    for i in landed:
        table = _ENDOWMENT_WEIGHTS[terrain[i]]
        kinds = [k for k, w in table for _ in range(w)]
        count = rng.choice((0, 1, 1, 2))
        picked: Dict[str, int] = {}
        for _ in range(count):
            kind = rng.choice(kinds)
            if kind not in picked:
                picked[kind] = rng.randint(1, 3)
        endowments[i] = picked
    for kind, need in ENDOWMENT_MINIMUMS.items():
        while sum(1 for i in landed if kind in endowments[i]) < need:
            eligible = [i for i in landed if kind not in endowments[i]
                        and (kind != "harbor" or terrain[i] == "coast")]
            if not eligible:
                eligible = [i for i in landed if kind not in endowments[i]]
            if not eligible:
                break
            endowments[rng.choice(eligible)][kind] = rng.randint(1, 3)

    # Names, population, and the final Province objects.
    used_names: Set[str] = set()
    pid_of = {region: pid for pid, region in enumerate(landed)}
    provinces: Dict[int, Province] = {}
    for region in landed:
        pid = pid_of[region]
        while True:
            name = rng.choice(_NAME_PARTS_A) + rng.choice(_NAME_PARTS_B)
            if rng.random() < 0.15:
                name = f"{name} {rng.choice(_NAME_SUFFIXES)}"
            if name not in used_names:
                used_names.add(name)
                break
        lo, hi = POPULATION_RANGE[terrain[region]]
        population = rng.randint(lo, hi)
        if "farmland" in endowments[region]:
            population = int(population * FARMLAND_POP_BONUS)
        cells = region_cells[region]
        center = (sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells))
        provinces[pid] = Province(
            pid=pid, name=name, terrain=terrain[region], endowments=endowments[region],
            cells=cells, center=center,
            neighbors={pid_of[n] for n in adj[region]},
            population=population,
        )

    links: Dict[Tuple[int, int], Link] = {}
    for pid, prov in provinces.items():
        for n in prov.neighbors:
            key = (min(pid, n), max(pid, n))
            if key not in links:
                links[key] = Link(a=key[0], b=key[1])
    return Atlas(provinces, links)
