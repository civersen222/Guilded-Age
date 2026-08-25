import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
import pygame
pygame.font.init()
import re, copy, glob, traceback, shutil
import uuid

import gilded.ui.widgets as W
from gilded.ui import app as appmod
from gilded.chassis import TURN_BUDGET
import gilded.endings as endings

LENGTH_WORDS = {"turn","turns","century","age","ends","lasts","long","budget","over","last"}

class FontProxy:
    def __init__(self, f, captured):
        self._f = f; self._c = captured
    def render(self, text, *a, **k):
        self._c.append(str(text))
        return self._f.render(text, *a, **k)
    def __getattr__(self, name):
        return getattr(self._f, name)

def captured_draw(seed):
    captured = []
    W._font_cache.clear()
    real_sysfont = pygame.font.SysFont
    def fake_sysfont(*a, **k):
        return FontProxy(real_sysfont(*a, **k), captured)
    pygame.font.SysFont = fake_sysfont
    try:
        state = appmod.new_app_state(seed=seed)
        surf = pygame.Surface((1280, 900))
        state.view.draw(surf)
    finally:
        pygame.font.SysFont = real_sysfont
        W._font_cache.clear()
    return state, captured

def claims_from_strings(strings):
    claims = {}
    for s in strings:
        tokens = re.findall(r"\d+|\w+", s)
        for i, t in enumerate(tokens):
            if t.isdigit():
                window = tokens[max(0,i-4):i+5]
                if any(w.lower() in LENGTH_WORDS for w in window if not w.isdigit()):
                    claims.setdefault(s, set()).add(int(t))
    return claims

def regions(state):
    return state.view.regions._regions

def center(region):
    r = region.rect
    return (r.left + r.right)//2, (r.top + r.bottom)//2

def bar1(seed):
    state, _ = captured_draw(seed)
    clicks = 0
    for _ in range(12):
        guide = [r for r in regions(state) if r.group == "guide" and r.state == W.RegionState.ENABLED]
        if not guide:
            break
        region = guide[0]
        if not region.hint:
            break
        cx, cy = center(region)
        action = state.view.handle_click((cx, cy))
        clicks += 1
        if action:
            appmod._apply_action(state, action)
        if state.game is None:
            break
        if state.game.turn >= 2:
            break
        # regions are rebuilt at draw time — redraw before reading again
        state.view.draw(pygame.Surface((1280, 900)))
    return clicks, state.game.turn if state.game else None

def bar2(seed):
    _, captured = captured_draw(seed)
    claims = claims_from_strings(captured)
    nums = set()
    for s, ns in claims.items():
        nums.update(ns)
    return len(nums) > 0, (nums == {TURN_BUDGET}), nums

def bar3(seed, sandbox_dir):
    """Find the save control by clicking every enabled region on every tab in a
    sandbox; whichever click creates a GILDEDSAVE file is the save control.
    Then click it for real, play 5 more turns, and find the region whose click
    brings the turn back to the earlier value."""
    import tempfile, copy as _copy
    os.makedirs(sandbox_dir, exist_ok=True)
    orig_cwd = os.getcwd()
    try:
        os.chdir(sandbox_dir)
        state, _ = captured_draw(seed)
        view = state.view
        # walk every tab, scanning enabled regions for the save control
        tabs = [r for r in view.regions._regions if r.group == "tabs"]
        save_region = None
        for tab in tabs:
            if tab.action:
                appmod._apply_action(state, tab.action)
            surf = pygame.Surface((1280, 900))
            view.draw(surf)
            for region in view.regions._regions:
                if region.state != W.RegionState.ENABLED:
                    continue
                cx, cy = center(region)
                before = set(glob.glob(os.path.join(sandbox_dir, "*.gsave")))
                try:
                    action = view.handle_click((cx, cy))
                    if action:
                        appmod._apply_action(state, action)
                except Exception:
                    continue
                after = set(glob.glob(os.path.join(sandbox_dir, "*.gsave")))
                for f in after - before:
                    with open(f, "rb") as fh:
                        if fh.read(11).startswith(b"GILDEDSAVE"):
                            save_region = region
                            break
                if save_region is not None:
                    break
                if not region.hint:
                    return False, "save control has empty hint", False, False
            if save_region is not None:
                break
        if save_region is None:
            return False, "no region wrote a GILDEDSAVE file", False, False
        if not save_region.hint:
            return False, "save control has empty hint", False, False
        # click it for real, play five more turns
        surf = pygame.Surface((1280, 900))
        view.draw(surf)
        cx, cy = center(save_region)
        action = view.handle_click((cx, cy))
        if action:
            appmod._apply_action(state, action)
        saved_turn = state.game.turn
        save_files = set(glob.glob(os.path.join(sandbox_dir, "*.gsave")))
        saved_bytes = {}
        for f in save_files:
            with open(f, "rb") as fh:
                saved_bytes[f] = fh.read()
        for _ in range(5):
            view.draw(pygame.Surface((1280, 900)))
            et = [r for r in view.regions._regions
                  if r.action is not None and "end_turn" in r.action
                  and r.state == W.RegionState.ENABLED]
            if not et:
                break
            cx, cy = center(et[0])
            action = view.handle_click((cx, cy))
            if action:
                appmod._apply_action(state, action)
        load_ok = False
        tabs = [r for r in state.view.regions._regions if r.group == "tabs"]
        for tab in tabs:
            appmod._apply_action(state, tab.action)
            state.view.draw(pygame.Surface((1280, 900)))
            for region in list(state.view.regions._regions):
                if region.state != W.RegionState.ENABLED:
                    continue
                cx2, cy2 = center(region)
                action = state.view.handle_click((cx2, cy2))
                if not action:
                    continue
                for f in glob.glob(os.path.join(sandbox_dir, "*.gsave")):
                    if f in saved_bytes:
                        with open(f, "wb") as fh:
                            fh.write(saved_bytes[f])
                try:
                    appmod._apply_action(state, action)
                except Exception:
                    continue
                if (state.game.turn == saved_turn and
                        (getattr(state.view, "game", state.game).turn == saved_turn)):
                    load_ok = True
                    break
            if load_ok:
                break
        # the view must still draw
        state.view.draw(pygame.Surface((1280, 900)))
        return True, f"saved at turn {saved_turn}", True, load_ok
    finally:
        os.chdir(orig_cwd)

def bar4(seed):
    nonce = uuid.uuid4().hex[:10]
    logpath = os.path.join(os.getcwd(), "gilded_crash.log")
    if os.path.exists(logpath):
        os.remove(logpath)
    state, _ = captured_draw(seed)
    view = state.view
    orig = view.draw
    def raising(surface, _n=nonce):
        raise RuntimeError(f"CRASH_NONCE_{_n}")
    view.draw = raising
    raised = None
    try:
        appmod.step_once(state)
    except Exception as e:
        raised = e
    view.draw = orig
    if raised is not None:
        return False, f"step_once raised: {raised}", False, False
    # subsequent healthy step_once returns truthy
    state2, _ = captured_draw(seed)
    ok_result = bool(appmod.step_once(state2))
    logtext = ""
    if os.path.exists(logpath):
        with open(logpath, encoding="utf-8") as f:
            logtext = f.read()
    found_nonce = nonce in logtext
    found_tb = "Traceback" in logtext
    return True, f"result={ok_result}", found_nonce, found_tb

def bar5():
    from gilded.chassis import GildedGame
    values = []
    for seed in range(24):
        g = GildedGame(seed)
        house = sorted(g.houses)[0]
        while g.turn < 10 and g.turn <= 71:
            g.end_turn()
        if g.turn < 10:
            continue
        values.append(endings.judge(g, house).axes["blood"])
    buckets = set(int(v // 5) * 5 for v in values)
    span = (max(values) - min(values)) if values else 0.0
    pinned = sum(1 for v in values if v == 100.0)
    ok = (len(buckets) >= 5 and span >= 20.0 and pinned <= 20)
    return values, buckets, span, pinned, ok

print(f"TURN_BUDGET = {TURN_BUDGET}")
print("=== BAR 1: blind walk (turn 2 within 12 clicks) ===")
b1 = 0
for seed in range(24):
    clicks, turn = bar1(seed)
    ok = clicks <= 12 and turn is not None and turn >= 2
    if ok: b1 += 1
    print(f"  seed {seed}: {clicks} clicks, turn={turn} -> {'OK' if ok else 'FAIL'}")
print(f"Bar 1: {b1}/24")
print()

print("=== BAR 2: length claim == TURN_BUDGET ===")
b2claim = b2ok = 0
for seed in range(24):
    has, correct, nums = bar2(seed)
    if has: b2claim += 1
    if has and correct: b2ok += 1
    print(f"  seed {seed}: claim={has} correct={correct} nums={nums}")
print(f"Bar 2: {b2claim}/24 claim, {b2ok}/24 correct")
print()

print("=== BAR 3: put down and picked up by clicking ===")
import tempfile
b3 = 0
for seed in range(6):
    sandbox = tempfile.mkdtemp(prefix="gate3_")
    try:
        ok, info, save_found, load_found = bar3(seed, sandbox)
    except Exception as e:
        ok, info, save_found, load_found = False, f"raised: {e}", False, False
    if ok and save_found and load_found:
        b3 += 1
    print(f"  seed {seed}: save={save_found} load={load_found} {info} -> {'OK' if ok and save_found and load_found else 'FAIL'}")
    shutil.rmtree(sandbox, ignore_errors=True)
print(f"Bar 3: {b3}/6")
print()

print("=== BAR 4: crash handler ===")
b4 = 0
for seed in range(4):
    no_raise, info, fn, ftb = bar4(seed)
    ok = no_raise and fn and ftb
    if ok: b4 += 1
    print(f"  seed {seed}: no_raise={no_raise} {info} nonce={fn} traceback={ftb} -> {'OK' if ok else 'FAIL'}")
print(f"Bar 4: {b4}/4")
print()

print("=== BAR 5: blood axis ===")
values, buckets, span, pinned, ok5 = bar5()
print(f"  values={values}")
print(f"  buckets={len(buckets)} span={span:.1f} pinned={pinned} -> {'OK' if ok5 else 'FAIL'}")
print()

print("=== SUMMARY ===")
print(f"Bar1={b1}/24 Bar2={b2ok}/24 Bar3={b3}/6 Bar4={b4}/4 Bar5={'OK' if ok5 else 'FAIL'}")
