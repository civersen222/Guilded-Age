"""Great Houses: spread capitals, contiguous clusters, minors as buffer (spec section 3)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from gilded.world import MINOR_OWNER, Atlas

HOUSE_NAMES = ["Vantrell", "Karsgate", "Mordaine", "Ashworth", "Ferrenholt",
               "Duval-Corse", "Brandtner", "Ostreval"]
GREAT_HOUSE_COUNT = 7
STARTING_TREASURY = 2000.0
CLUSTER_MIN, CLUSTER_MAX = 5, 7
GROW_TARGET_MIN, GROW_TARGET_MAX = 5, 6   # leaves enough minors on small maps
CAPITAL_GARRISON, PROVINCE_GARRISON = 2, 1
MAX_ATTEMPTS = 30


@dataclass
class House:
    name: str
    capital: int                                        # pid
    treasury: float = STARTING_TREASURY
    is_player: bool = False
    prestige: float = 0.0
    at_war_with: Set[str] = field(default_factory=set)
    truces: Dict[str, int] = field(default_factory=dict)      # house -> expiry turn
    relations: Dict[str, int] = field(default_factory=dict)   # house -> -100..100


def assign_houses(atlas: Atlas, seed: int) -> Dict[str, House]:
    """Deterministic: capitals maximally spread, clusters grown by BFS round-robin."""
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(seed * 991 + attempt)
        houses = _try_assign(atlas, rng)
        if houses is not None:
            return houses
    raise RuntimeError(f"house assignment failed for seed {seed}")


def _largest_component(atlas: Atlas) -> List[int]:
    seen: Set[int] = set()
    best: List[int] = []
    for start in sorted(atlas.provinces):
        if start in seen:
            continue
        comp = [start]
        seen.add(start)
        queue = [start]
        while queue:
            cur = queue.pop(0)
            for n in sorted(atlas.provinces[cur].neighbors):
                if n not in seen:
                    seen.add(n)
                    comp.append(n)
                    queue.append(n)
        if len(comp) > len(best):
            best = comp
    return sorted(best)


def _euclid(atlas: Atlas, a: int, b: int) -> float:
    (ax, ay), (bx, by) = atlas.provinces[a].center, atlas.provinces[b].center
    return math.hypot(ax - bx, ay - by)


def _try_assign(atlas: Atlas, rng: random.Random) -> Optional[Dict[str, House]]:
    component = _largest_component(atlas)
    if len(component) < GREAT_HOUSE_COUNT * CLUSTER_MIN + 5:
        return None

    # Capitals: population-weighted start, then near-farthest-point picks.
    # rng jitter (top-3 choice) lets retry attempts escape boxed-in layouts.
    by_pop = sorted(component, key=lambda pid: (-atlas.provinces[pid].population, pid))
    capitals = [rng.choice(by_pop[:3])]
    while len(capitals) < GREAT_HOUSE_COUNT:
        scored = sorted(
            (pid for pid in component if pid not in capitals),
            key=lambda pid: (-min(_euclid(atlas, pid, c) for c in capitals), pid),
        )
        capitals.append(rng.choice(scored[:3]))

    houses: Dict[str, House] = {}
    owner_of: Dict[int, str] = {}
    frontier: Dict[str, List[int]] = {}
    target: Dict[str, int] = {}
    for i, cap in enumerate(capitals):
        name = HOUSE_NAMES[i]
        houses[name] = House(name=name, capital=cap)
        owner_of[cap] = name
        frontier[name] = [cap]
        target[name] = rng.randint(GROW_TARGET_MIN, GROW_TARGET_MAX)

    # Round-robin BFS growth keeps clusters contiguous and fair.
    grown = {name: 1 for name in houses}
    progress = True
    while progress:
        progress = False
        for name in houses:
            if grown[name] >= target[name]:
                continue
            candidates: List[int] = []
            for pid in frontier[name]:
                for n in sorted(atlas.provinces[pid].neighbors):
                    if n not in owner_of and n not in candidates:
                        candidates.append(n)
            if not candidates:
                continue
            pick = candidates[0]
            owner_of[pick] = name
            frontier[name].append(pick)
            grown[name] += 1
            progress = True

    if any(grown[name] < CLUSTER_MIN for name in houses):
        return None

    for prov in atlas.provinces.values():
        prov.owner = MINOR_OWNER
        prov.garrison = PROVINCE_GARRISON
    for pid, name in owner_of.items():
        atlas.provinces[pid].owner = name
    for house in houses.values():
        atlas.provinces[house.capital].garrison = CAPITAL_GARRISON
    for a in houses:
        for b in houses:
            if a != b:
                houses[a].relations[b] = 0
    return houses
