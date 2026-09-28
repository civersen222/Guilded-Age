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
from gilded.chassis import GildedGame
from gilded.ui import widgets
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
    return action


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


# ---------------------------------------------------------------------------
# C9.2 keybinds: a table in the settings file, a rebind on the Settings
# screen, a loop that obeys it.
# ---------------------------------------------------------------------------

def _post_keydown(s, key_name):
    code = pygame.key.key_code(key_name)
    assert code is not None, f"key name {key_name!r} does not resolve"
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=code))
    step_once(s)
    pygame.event.clear()


def _rebind_save_region(s):
    """The Settings-screen region that rebinds the 'save' action."""
    for r in _regions(s):
        a = r.action
        if a.get("bind") == "save" or a.get("rebind") == "save":
            return r
    raise AssertionError("no drawn region rebinds 'save'")


def test_c92a_keybinds_table(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "menu")
    kb = s.settings.keybinds
    assert isinstance(kb, dict)
    assert len(kb) >= 4, kb
    codes = set()
    for action_name, key_name in kb.items():
        code = pygame.key.key_code(key_name)
        assert code is not None, f"{key_name!r} does not resolve to a keycode"
        assert code not in codes, f"two actions share key {key_name!r}"
        codes.add(code)
    assert "save" in kb, kb


def test_c92b_keybind_drives_game(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    assert s.game is not None
    if os.path.isfile(s.save_path):
        os.remove(s.save_path)
    _post_keydown(s, s.settings.keybinds["save"])
    assert os.path.isfile(s.save_path), "save keydown did not write the quicksave"
    with open(s.save_path, "rb") as f:
        assert f.read(11) == b"GILDEDSAVE "


def test_c92c_rebind_persists(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "menu")
    _press(s, next(r for r in _regions(s)
                   if r.action == {"menu": "settings"}))
    row = _press(s, _rebind_save_region(s))
    assert row == {"setting": "rebind", "bind": "save"}, row
    old_key = s.settings.keybinds["save"]
    new_key = next(k for k in ("f9", "f10", "f11", "f12", "f8", "f7", "f6")
                   if k not in s.settings.keybinds.values())
    _post_keydown(s, new_key)
    assert s.settings.keybinds["save"] == new_key
    with open(gsettings.settings_path(), "r", encoding="utf-8") as f:
        data = json.load(f)
    assert pygame.key.key_code(data["keybinds"]["save"]) == pygame.key.key_code(new_key)
    assert "window_size" in data, "rebind stripped the other settings"
    bytes_ = open(gsettings.settings_path(), "rb").read()

    # fresh launch, file deleted: back on the old key (file is the source)
    os.remove(gsettings.settings_path())
    s2 = _relaunch(7, "menu")
    assert s2.settings.keybinds["save"] == old_key
    if os.path.isfile(s2.save_path):
        os.remove(s2.save_path)
    _post_keydown(s2, new_key)
    assert not os.path.isfile(s2.save_path), "new key fired on a fresh default launch"

    # file written back: the new key is obeyed in a fresh game
    open(gsettings.settings_path(), "wb").write(bytes_)
    s3 = _relaunch(7, "game")
    assert s3.settings.keybinds["save"] == new_key
    if os.path.isfile(s3.save_path):
        os.remove(s3.save_path)
    _post_keydown(s3, new_key)
    assert os.path.isfile(s3.save_path)
    os.remove(s3.save_path)
    _post_keydown(s3, old_key)
    assert not os.path.isfile(s3.save_path), "old key must not fire once rebound"

    # gate-written JSON with a third key the game never captured
    with open(gsettings.settings_path(), "r", encoding="utf-8") as f:
        data = json.load(f)
    third = next(k for k in ("f9", "f10", "f11", "f12", "f8", "f7", "f6")
                 if k not in data["keybinds"].values())
    data["keybinds"]["save"] = third
    with open(gsettings.settings_path(), "w", encoding="utf-8") as f:
        json.dump(data, f)
    s4 = _relaunch(7, "game")
    assert s4.settings.keybinds["save"] == third
    if os.path.isfile(s4.save_path):
        os.remove(s4.save_path)
    _post_keydown(s4, third)
    assert os.path.isfile(s4.save_path)
    with open(s4.save_path, "rb") as f:
        assert f.read(11) == b"GILDEDSAVE "


# ── C9.3 — saves screen: slots that save and load the WHOLE game ─────────────


def _saves_opener(s):
    for r in _regions(s):
        a = r.action
        if a.get("saves") is not None or "saves" in a.values():
            return r
    raise AssertionError("no drawn region opens the saves screen")


def _slot_regions(s):
    """Drawn regions carrying a slot id: {"load_slot": id} / {"save_slot": id},
    or {<any key>: "load_slot" | "save_slot", "slot": id}."""
    out = []
    for r in _regions(s):
        a = r.action
        sid = a.get("slot")
        if sid is None:
            continue
        kind = (a.get("load_slot") or a.get("save_slot")
                or next((v for v in a.values()
                         if v in ("load_slot", "save_slot")), None))
        if kind is not None:
            out.append((kind, sid, r))
    return out


def test_c93a_saves_screen(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = new_app_state(seed=7, start="menu")
    _press(s, _saves_opener(s))
    s.view.draw(s.screen)
    rows = widgets.take_text_rows()
    slot_re = _slot_regions(s)
    ids = {sid for _, sid, _ in slot_re}
    assert len(ids) >= 2, f"need >= 2 slots, drew {ids!r}"
    labels = {}
    for kind, sid, r in slot_re:
        hits = [t for rect, t in rows if rect.colliderect(r.rect)]
        assert hits, f"slot {sid} has no label text"
        labels.setdefault(sid, hits[0])
    assert len(set(labels.values())) >= 2, labels


def test_c93b_save_round_trips_state(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    svd = os.path.join(os.getcwd(), "saves")
    if os.path.isdir(svd):
        for f in os.listdir(svd):
            if f.endswith(".gsave"):
                os.remove(os.path.join(svd, f))
    s = _relaunch(7, "game")
    house = s.house
    s.game.end_turn()
    s.game.end_turn()
    s.game.end_turn()
    s.game.houses[house].treasury += 777.25
    turn, treas = s.game.turn, round(s.game.houses[house].treasury, 4)
    _press(s, _saves_opener(s))
    kind, sid, r = next(x for x in _slot_regions(s)
                        if x[0] == "save_slot")
    _press(s, r)
    files = [os.path.join(svd, f) for f in os.listdir(svd)
             if f.endswith(".gsave")]
    files = [f for f in files
             if open(f, "rb").read(11) == b"GILDEDSAVE "]
    assert files, "no slot file under <cwd>/saves/"
    g = gsave.load_game(files[0])
    assert isinstance(g, GildedGame)
    assert (g.turn, round(g.houses[house].treasury, 4)) == (turn, treas)

    s2 = _relaunch(7, "menu")
    _press(s2, _saves_opener(s2))
    load_r = next(r for kind, sid2, r in _slot_regions(s2)
                  if kind == "load_slot" and sid2 == sid)
    _press(s2, load_r)
    assert s2.game is not None
    assert (s2.game.turn, round(s2.game.houses[house].treasury, 4)) \
        == (turn, treas)
    s3 = _relaunch(7, "game")
    assert (s3.game.turn, round(s3.game.houses[house].treasury, 4)) \
        != (turn, treas)


# ── C9.5 — packaging ──────────────────────────────────────────────────────────

import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_c9_5a_packaging_declares():
    with open(os.path.join(_REPO, "pyproject.toml"), "rb") as f:
        doc = tomllib.load(f)
    bs = doc["build-system"]
    assert bs.get("requires"), "build-system requires must be non-empty"
    assert bs["build-backend"] == "setuptools.build_meta"
    proj = doc["project"]
    assert "gild" in proj["name"]
    assert proj.get("version")
    entries = sorted(proj["scripts"].items())
    script, target = entries[0]
    module, _, callable_ = target.partition(":")
    assert callable_
    assert module == "gilded" or module.startswith("gilded.")
    find = doc["tool"]["setuptools"]["packages"]["find"]
    assert "gilded*" in find.get("include", [])


def test_c9_5b_packaging_launches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CIVKINGS_HEADLESS_FRAMES", "3")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import gilded.ui.app as app
    import gilded.__main__ as gmain
    captured = {}
    real_step = app.step_once

    def spy(state):
        running = real_step(state)
        if len(captured) < 3:
            size = pygame.display.get_surface().get_size()
            keys = [r.action for r in state.view.regions._regions
                    if isinstance(r.action, dict)]
            captured[len(captured)] = (
            size, bytes(state.screen.convert().get_buffer()), keys)
        return running

    monkeypatch.setattr(app, "step_once", spy)
    sys.argv = ["gilded"]
    result = gmain.main([])
    assert result in (0, None)
    assert len(captured) >= 1, "the launcher never flipped the display"
    size, last, keys = captured[len(captured) - 1]
    data = last
    n = len(data)
    assert n
    top = max(set(data), key=data.count)
    assert data.count(top) / n < 0.995, "the last frame is blank"
    first_keys = captured[0][2]
    assert {"menu": "new_game"} in first_keys, "the menu was never drawn"
    # run_app quit pygame; re-open the display, re-init the font
    # module, and drop the cached Font objects (invalid after quit)
    # so later tests in the session can still draw and render.
    from gilded.ui import widgets as _w
    _w._font_cache.clear()
    pygame.font.init()
    pygame.display.set_mode((1280, 900))


def test_c9_5c_packaging_builds(tmp_path):
    """Build the wheel from a COPY of the repo (never inside it)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in os.listdir(_REPO):
        if name in {"__pycache__", "build", "dist", "saves", "salvage",
                "docs", "legacy"}:
            continue
        if name.startswith("."):
            continue
        if name.endswith(".egg-info"):
            continue
        if name.startswith((".venv", "venv", "node_modules", ".claude",
                            ".cursor", ".vscode", ".idea")):
            continue
        src = os.path.join(_REPO, name)
        if name == "gilded" and os.path.isdir(src):
            dst = repo / name
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if d != "__pycache__"
                           and not d.endswith(".egg-info")]
                for fn in files:
                    if fn.endswith(".gsave"):
                        continue
                    rel = os.path.relpath(os.path.join(root, fn), src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), target)
        else:
            shutil.copy2(src, repo / name)
    outdir = tmp_path / "wheelout"
    outdir.mkdir()
    env = dict(os.environ)
    env.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYTHONIOENCODING="utf-8",
    )
    script = "import setuptools.build_meta as b; b.build_wheel(r'%s')" % outdir
    proc = subprocess.run([sys.executable, "-c", script], cwd=repo,
                          env=env, capture_output=True, text=True,
                          timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    wheels = list(outdir.glob("*.whl"))
    assert wheels, "no wheel came out of the build"
    z = zipfile.ZipFile(wheels[0])
    names = z.namelist()
    assert "gilded/__main__.py" in names
    assert "gilded/ui/app.py" in names
    ep = z.read([n for n in names if n.endswith("entry_points.txt")][0]).decode()
    assert "gilded = gilded.__main__:main" in ep
    assets = [n for n in names if n.startswith("gilded/assets/")]
    assert len(assets) >= 50, f"only {len(assets)} assets in the wheel"
    assert not any(n == "legacy" or n.startswith("legacy/") for n in names)
