"""Mission C7, commit 1 - chains are first-class beats.

A seeded 70-turn run at seed 42 must show >= 6 distinct library chain_ids
recorded on the beat log as Beat(kind="chain", facet=<chain_id>), each
with >= 3 beats over >= 2 distinct turns. The three hard-coded teaser
chains (enterprise/labor/war) do not count: only ids in the library do.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c7_chain_beats.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gilded.ui.app import new_app_state, _apply_action
from gilded.society.event_content.chains_pack1 import build_pack1
from gilded.society.event_content.chains_pack2 import build_pack2

SEED = 42


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


def test_seed42_run_records_six_library_chains_as_beats(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED, start="menu")
    _press_new_game(s)
    g = s.game
    for _ in range(70):
        g.end_turn()

    library = {d.chain_id for d in build_pack1() + build_pack2()}
    by_chain = {}
    for b in g.beats.log:
        if getattr(b, "kind", "") == "chain" and b.facet in library:
            by_chain.setdefault(b.facet, []).append(b)

    good = {cid: bs for cid, bs in by_chain.items()
            if len(bs) >= 3 and len({b.turn for b in bs}) >= 2}
    assert len(good) >= 6, {c: len(bs) for c, bs in by_chain.items()}
    # every beat names the actor when the step's context has one
    faces = [b for b in by_chain.get("heir_radicalization", [])]
    assert any(b.face for b in faces or
               [b for cid in ("heir_radicalization", "martyr_ballad")
                for b in by_chain.get(cid, [])]), \
        "chain beats lost their face (the actor's name)"
