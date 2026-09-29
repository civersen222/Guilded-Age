"""Mission C7, commit 2 - the chain library spans the whole act structure.

The library holds >= 18 ChainDefs, every one of them >= 3 steps, and in a
70-turn run at seeds 42 and 7 at least 2 distinct chains have a beat in
EACH act band: turns 1-25, 26-50, 51-70. Triggers read the live world,
never a turn number.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c7_bands.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gilded.ui.app import new_app_state, _apply_action
from gilded.society.event_content.chains_pack1 import build_pack1
from gilded.society.event_content.chains_pack2 import build_pack2
from gilded.society.event_content.chains_pack3 import build_pack3

TEASERS = {"enterprise", "labor", "war"}


def _library():
    return build_pack1() + build_pack2() + build_pack3()


def _press_new_game(s):
    s.view.draw(s.screen)
    regions = [r for r in s.view.regions._regions
               if getattr(r, "group", "") == "menu"
               and isinstance(r.action, dict)
               and r.action.get("menu") == "new_game"]
    assert regions, "no new_game region on the menu"
    action = s.view.handle_click(regions[0].rect.center)
    assert action is not None
    _apply_action(s, action)


def test_library_depth_and_step_count():
    defs = _library()
    assert len(defs) >= 18, f"library has {len(defs)} defs"
    for d in defs:
        assert len(d.steps) >= 3, f"{d.chain_id}: only {len(d.steps)} steps"


def _bands_of(seed):
    s = new_app_state(seed=seed, start="menu")
    _press_new_game(s)
    g = s.game
    for _ in range(70):
        g.end_turn()
    lib = {d.chain_id for d in _library()}
    bands = {1: set(), 2: set(), 3: set()}
    for b in g.beats.log:
        if getattr(b, "kind", "") != "chain" or b.facet not in lib:
            continue
        if b.facet in TEASERS:
            continue
        if b.turn <= 25:
            bands[1].add(b.facet)
        elif b.turn <= 50:
            bands[2].add(b.facet)
        else:
            bands[3].add(b.facet)
    return bands


def test_act_bands_covered_on_seeds_42_and_7(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for seed in (42, 7):
        bands = _bands_of(seed)
        for band, members in bands.items():
            assert len(members) >= 2, (
                f"seed {seed} act band {band} has only "
                f"{sorted(members)}; need >= 2 distinct chains")
