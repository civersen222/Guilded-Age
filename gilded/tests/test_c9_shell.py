"""Mission C9 Wave 1 — ship shell: the committed self-check.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c9_shell.py -q

C9.1 the Settings screen cycles the resolution presets and persists the
choice; C9.4 the frame clock follows Settings.target_fps and the file is
the only source of truth across fresh launches.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import json
import pygame

from gilded import settings as gsettings
from gilded import save as gsave
from gilded.ui.app import new_app_state, step_once, _apply_action


def _clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for p in (gsettings.settings_path(), gsave.quicksave_path()):
        if os.path.isfile(p):
            os.remove(p)


def _relaunch(seed, start):
    pygame.display.quit()
    return new_app_state(seed=seed, start=start)


def _regions(s):
    s.view.draw(s.screen)
    return [r for r in s.view.regions._regions if isinstance(r.action, dict)]


def _press(s, region):
    action = s.view.handle_click(region.rect.center)
    assert action is not None, f"press refused: {getattr(region, 'reason', None)!r}"
    _apply_action(s, action)


def _res_regions(s):
    """Drawn regions whose action names a resolution: a key 'resolution' or
    'window_size', or a string value that is one of those two."""
    out = []
    for r in _regions(s):
        a = r.action
        hits = (a.get("resolution") is not None
                or a.get("window_size") is not None
                or "resolution" in a.values()
                or "window_size" in a.values())
        if hits:
            out.append(r)
    return out


def test_c9_1a_resolution_presets(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = new_app_state(seed=7, start="menu")
    sizes = {(int(w), int(h)) for w, h in s.settings.resolutions}
    assert len(sizes) >= 3
    # open the Settings screen by pressing its drawn menu region
    menu = [r for r in _regions(s) if r.action == {"menu": "settings"}]
    assert menu
    _press(s, menu[0])
    regs = _res_regions(s)
    assert regs, "no resolution region drawn on the Settings screen"


def _press_resolution(s):
    """Press the resolution region (redrawing before each press); if the live
    size does not change, press the next region — up to one more press than
    there are regions."""
    before = pygame.display.get_surface().get_size()
    for i in range(3):
        regs = _res_regions(s)
        assert regs, "no resolution region to press"
        _press(s, regs[i % len(regs)])
        after = pygame.display.get_surface().get_size()
        if after != before:
            return before, after
    raise AssertionError("resolution presses never changed the live size")


def test_c9_1b_resolution_applies(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = new_app_state(seed=7, start="menu")
    menu = [r for r in _regions(s) if r.action == {"menu": "settings"}]
    _press(s, menu[0])
    before, after = _press_resolution(s)
    assert after != before
    assert after in {(w, h) for w, h in s.settings.resolutions}
    assert s.screen.get_size() == after
    assert pygame.display.get_surface() is s.screen


def test_c9_1c_resolution_persists(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = new_app_state(seed=7, start="menu")
    menu = [r for r in _regions(s) if r.action == {"menu": "settings"}]
    _press(s, menu[0])
    _press_resolution(s)
    chosen = tuple(s.settings.window_size)
    p = gsettings.settings_path()
    assert os.path.isfile(p)
    data = json.load(open(p, "r", encoding="utf-8"))
    assert tuple(data["window_size"]) == chosen
    # delete the file and launch fresh: the live size is NOT the chosen one
    os.remove(p)
    s2 = _relaunch(7, "menu")
    assert tuple(pygame.display.get_surface().get_size()) != chosen
    # write the bytes back and launch fresh: both the live size and the
    # settings object equal the chosen size
    data2 = json.load(open(p, "r", encoding="utf-8")) if os.path.isfile(p) else None
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"window_size": list(chosen)}, f)
    s3 = _relaunch(7, "menu")
    assert tuple(pygame.display.get_surface().get_size()) == chosen
    assert tuple(s3.settings.window_size) == chosen


class _RecClock:
    def __init__(self):
        self.args = []
        self._c = pygame.time.Clock()

    def tick(self, f=None):
        self.args.append(f)
        return self._c.tick(f)

    def tick_busy_loop(self, f=None):
        self.args.append(f)
        return self._c.tick_busy_loop(f)


def test_c9_4a_fps_guard(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = new_app_state(seed=7, start="game")
    assert isinstance(s.target_fps, int) and s.target_fps > 0
    m = _relaunch(7, "menu")
    assert m.target_fps == s.target_fps
    s.clock = _RecClock()
    for _ in range(3):
        step_once(s)
    assert len(s.clock.args) == 3
    assert all(a == s.target_fps for a in s.clock.args)
    m.clock = _RecClock()
    for _ in range(2):
        step_once(m)
    assert all(a == m.target_fps for a in m.clock.args)


def test_c9_4b_fps_follows_settings(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    st = gsettings.load_settings()
    first = st.target_fps
    second = 72 if first == 48 else 48
    st.target_fps = second
    gsettings.save_settings(st)
    data = json.load(open(gsettings.settings_path(), "r", encoding="utf-8"))
    assert data["target_fps"] == second
    s = new_app_state(seed=7, start="game")
    assert s.target_fps == second
    s.clock = _RecClock()
    for _ in range(3):
        step_once(s)
    assert len(s.clock.args) == 3
    assert all(a == second for a in s.clock.args)
    # delete the file and launch fresh: back at the first value
    os.remove(gsettings.settings_path())
    s2 = _relaunch(7, "game")
    assert s2.target_fps == first
    s2.clock = _RecClock()
    for _ in range(3):
        step_once(s2)
    assert all(a == first for a in s2.clock.args)
    # the gate's own file: a third value
    third = 50 if second != 50 else 55
    with open(gsettings.settings_path(), "w", encoding="utf-8") as f:
        json.dump({"window_size": [1280, 900], "target_fps": third}, f)
    s3 = _relaunch(7, "game")
    assert s3.target_fps == third
    s3.clock = _RecClock()
    for _ in range(3):
        step_once(s3)
    assert all(a == third for a in s3.clock.args)
