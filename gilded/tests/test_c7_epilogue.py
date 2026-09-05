"""Mission C7 wave 4, commit 3 - the epilogue remembers.

endings.judge(game, house).text must name at least 2 characters who have
history and quote at least one entry's text verbatim (>= 20 characters).

Run EXACTLY as:
    python -m pytest gilded/tests/test_c7_epilogue.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gilded.ui.app import new_app_state, _apply_action
from gilded.endings import judge

TURNS = 70


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


def _run(seed):
    s = new_app_state(seed=seed, start="menu")
    _press_new_game(s)
    g = s.game
    for _ in range(TURNS):
        g.end_turn()
    return g


def _assert_epilogue_remembers(g):
    player = [h for h in g.houses if g.houses[h].is_player][0]
    realm = g.realms[player]
    with_hist = [c for c in realm.characters
                 if getattr(c, "history", None)]
    assert len(with_hist) >= 2, "no characters carry history to remember"
    ep = judge(g, player)
    text = ep.text
    named = [c.name for c in with_hist if c.name in text]
    assert len(named) >= 2, \
        f"epilogue names < 2 characters with history: {named}"
    quoted = [e["text"] for c in with_hist for e in c.history
              if len(e["text"]) >= 20 and e["text"] in text]
    assert quoted, "no history entry (>= 20 chars) quoted verbatim in the " \
                   "epilogue"


def test_seed42_epilogue_remembers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_epilogue_remembers(_run(42))


def test_seed7_epilogue_remembers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_epilogue_remembers(_run(7))
