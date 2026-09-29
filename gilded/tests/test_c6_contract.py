"""Mission C6 Wave 1 — the vertical slice: Menu -> Play -> Ending.

The committed self-check. Run EXACTLY as:
    python -m pytest gilded/tests/test_c6_contract.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import subprocess
import sys
from gilded.ui.app import new_app_state, _apply_action
from gilded.ui.widgets import RegionState

SEED = 42


def _regions(s, group):
    s.view.draw(s.screen)
    return [r for r in s.view.regions._regions
            if getattr(r, "group", "") == group
            and isinstance(r.action, dict)]


def _press(s, region):
    action = s.view.handle_click(region.rect.center)
    assert action is not None, f"press refused: {getattr(region, 'reason', None)!r}"
    _apply_action(s, action)


def _menu(s):
    return {r.action.get("menu"): r for r in _regions(s, "menu")}


def test_menu_boots_and_new_game_plays(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED, start="menu")
    assert s.game is None
    menu = _menu(s)
    assert {"new_game", "continue", "settings", "quit"} <= set(menu)
    cont = menu["continue"]
    assert cont.state == RegionState.DISABLED
    assert (cont.reason or "").strip()
    _press(s, menu["new_game"])
    assert s.game is not None and len(s.game.houses) >= 6
    s.game.end_turn()
    s.view.draw(s.screen)


def test_continue_loads_save(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED, start="menu")
    _press(s, _menu(s)["new_game"])
    for _ in range(4):
        s.game.end_turn()
    import gilded.save as gsave
    writer = getattr(gsave, "save_game", None) or getattr(gsave, "save", None)
    writer(s.game, s.save_path)
    s2 = new_app_state(seed=SEED, start="menu")
    cont = _menu(s2)["continue"]
    assert cont.state == RegionState.ENABLED
    _press(s2, cont)
    assert s2.game is not None and s2.game.turn >= 4


def test_settings_persist_across_process(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED, start="menu")
    _press(s, _menu(s)["settings"])
    setts = {r.action.get("setting"): r for r in _regions(s, "settings")}
    _press(s, setts["mute"])
    assert (tmp_path / "gilded_settings.json").exists()
    p = subprocess.run(
        [sys.executable, "-c",
         "from gilded.settings import load_settings; "
         "import sys; sys.exit(0 if load_settings().mute else 1)"],
        cwd=tmp_path, env={**os.environ,
                           "PYTHONPATH": os.getcwd()},
        capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr


def test_audio_registry_real_and_mutable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from gilded import audio
    from gilded.settings import Settings
    for e in ("ui_press", "end_turn", "war_declared",
              "beat", "ending", "ambient"):
        assert e in audio.SOUND_EVENTS, e
        assert os.path.isfile(audio.resolve(e)), e
    assert audio.play("ui_press", Settings(mute=True)) is False
    assert audio.play("ui_press", Settings(mute=False)) in (True, False)


def test_no_text_overlap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED)
    for stop in (0, 10):
        while s.game.turn < stop:
            s.game.end_turn()
        for tab in ("House", "Powers", "Atlas"):
            s.view.active_tab = tab
            s.view.draw(s.screen)
            rows = s.view.text_rows
            assert rows, f"{tab}: no text rows"
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    assert not rows[i][0].colliderect(rows[j][0]), \
                        (tab, stop, rows[i][1][:40], rows[j][1][:40])


def test_slice_run_onboards_chains_ends(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from gilded.endings import check_ending, judge
    s = new_app_state(seed=SEED, start="menu")
    _press(s, _menu(s)["new_game"])
    g, house = s.game, s.house
    ended_at = None
    for t in range(1, 71):
        g.end_turn()
        if ended_at is None and check_ending(g, house):
            ended_at = t
    ob = {b.facet for b in g.beats.log
          if getattr(b, "kind", "") == "onboarding" and b.turn <= 5}
    assert {"win", "orders", "ambitions", "war", "turn"} <= ob, ob
    chains = {}
    for b in g.beats.log:
        if getattr(b, "kind", "") == "chain":
            chains.setdefault(b.facet, []).append(b)
    good = [c for c, bs in chains.items()
            if len(bs) >= 3 and len({b.turn for b in bs}) >= 2]
    assert len(good) >= 3, {c: len(bs) for c, bs in chains.items()}
    assert ended_at is not None, "no ending within 70 turns"
    assert judge(g, house).ending_key


_COMPLETENESS_PROBE = r"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
rendered = set()
class _F(pygame.font.Font):
    def render(self, text, *a, **kw):
        if isinstance(text, str) and text.strip():
            rendered.add(text)
        return super().render(text, *a, **kw)
pygame.font.Font = _F   # BEFORE any gilded import: widgets caches fonts
from gilded.ui.app import new_app_state
s = new_app_state(seed=42)
for tab in ("House", "Powers", "Atlas"):
    s.view.active_tab = tab
    s.view.draw(s.screen)      # warm-up draw fills caches
    rendered.clear()
    s.view.draw(s.screen)      # measured draw
    rows = {t for _, t in s.view.text_rows if t.strip()}
    missing = rendered - rows
    assert not missing, (tab, sorted(missing)[:5], len(missing))
print("COMPLETE")
"""


def test_text_rows_complete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p = subprocess.run(
        [sys.executable, "-c", _COMPLETENESS_PROBE],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": repo},
        capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "COMPLETE" in p.stdout
