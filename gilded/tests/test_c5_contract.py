import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import statistics
import time
from gilded.ui.app import new_app_state

SEEDS = (7, 11, 13)
GENTRY_FACETS = {"share", "board", "marriage"}

def _names(g):
    gen = g.gentry
    if hasattr(gen, "keys"):
        return {str(k) for k in gen.keys()}
    return {str(getattr(x, "name", x)) for x in gen}

def test_scale_counts():
    for seed in SEEDS:
        g = new_app_state(seed=seed).game
        assert 6 <= len(g.houses) <= 8
        assert 20 <= len(_names(g)) <= 30
        assert 150 <= len(g.atlas.provinces) <= 250

def test_gentry_light_sim_beats():
    for seed in SEEDS:
        g = new_app_state(seed=seed).game
        base = len(g.beats.log)
        for _ in range(60):
            g.end_turn()
        ev = [b for b in g.beats.log[base:]
              if b.kind == "gentry" and b.facet in GENTRY_FACETS]
        assert ev, f"seed {seed}: no gentry share/board/marriage beat in 60 turns"

def test_gentry_mobility_somewhere():
    moved = False
    for seed in SEEDS:
        g = new_app_state(seed=seed).game
        names0 = _names(g)
        base = len(g.beats.log)
        for _ in range(60):
            g.end_turn()
        names1 = _names(g)
        houses1 = {str(h) for h in g.houses}
        rose = names0 & houses1
        fell = names0 - names1 - houses1
        mob = [b for b in g.beats.log[base:]
               if b.kind == "gentry" and b.facet in {"rise", "fall"}]
        if (rose or fell) and mob:
            moved = True
    assert moved, "no seed showed gentry mobility (membership change + rise/fall beat)"

def test_end_turn_performance():
    g = new_app_state(seed=7).game
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        g.end_turn()
        times.append((time.perf_counter() - t0) * 1000.0)
    assert statistics.median(times) <= 30.6
