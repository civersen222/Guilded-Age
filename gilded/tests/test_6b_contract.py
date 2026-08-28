import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import re
from gilded.ui.app import new_app_state, _apply_action
from gilded.ui.widgets import RegionState
from gilded.fronts import declare_war, WarGoal
from gilded.docket import initiative

SEEDS = (7, 11, 42)

def _center(g, house):
    pts = [p.center for p in g.atlas.provinces.values() if p.owner == house]
    return (sum(x for x, _ in pts) / len(pts),
            sum(y for _, y in pts) / len(pts))

def _nearest(g, p):
    me = _center(g, p)
    return min((h for h in g.houses if h != p),
               key=lambda h: (_center(g, h)[0] - me[0]) ** 2
               + (_center(g, h)[1] - me[1]) ** 2)

def _open_drawer(s):
    s.view.active_tab = "Atlas"
    s.view.draw(s.screen)
    tog = [r for r in s.view.regions._regions
           if isinstance(r.action, dict) and "toggle_war_drawer" in r.action]
    assert tog, "war drawer toggle not drawn on Atlas"
    s.view.handle_click(tog[0].rect.center)
    assert s.view.war_drawer
    s.view.draw(s.screen)
    return [r for r in s.view.regions._regions
            if getattr(r, "group", "") == "war_actions"]

def _war_regions(s):
    s.view.draw(s.screen)
    return [r for r in s.view.regions._regions
            if getattr(r, "group", "") == "war_actions"]

def _press(s, region):
    action = s.view.handle_click(region.rect.center)
    assert action is not None, f"press refused: {region.reason!r}"
    _apply_action(s, action)

def test_fronts_form_even_far_apart():
    for seed in SEEDS:
        s = new_app_state(seed=seed)
        g, p = s.game, s.house
        me = _center(g, p)
        far = max((h for h in g.houses if h != p),
                  key=lambda h: (_center(g, h)[0] - me[0]) ** 2
                  + (_center(g, h)[1] - me[1]) ** 2)
        war = declare_war(g, p, far, WarGoal(kind="humble"))
        assert len(war.fronts) >= 1, f"seed {seed}: war on {far} has no front"

def test_declare_press_opens_war_with_fronts():
    for seed in SEEDS:
        s = new_app_state(seed=seed)
        g, p = s.game, s.house
        near = _nearest(g, p)
        wa = _open_drawer(s)
        decl = [r for r in wa if isinstance(r.action, dict)
                and r.action.get("declare_war") == near
                and r.state == RegionState.ENABLED]
        assert decl, f"seed {seed}: no enabled declare control for {near}"
        _press(s, decl[0])
        wars = [w for w in g.wars
                if {w.aggressor, w.defender} == {p, near}]
        assert len(wars) == 1 and len(wars[0].fronts) >= 1

def test_muster_lands_and_war_moves():
    s = new_app_state(seed=42)
    g, p = s.game, s.house
    near = _nearest(g, p)
    wa = _open_drawer(s)
    decl = [r for r in wa if isinstance(r.action, dict)
            and r.action.get("declare_war") == near
            and r.state == RegionState.ENABLED]
    assert decl
    _press(s, decl[0])
    war = [w for w in g.wars if {w.aggressor, w.defender} == {p, near}][0]
    landed = False
    for _ in range(3):
        musters = [r for r in _war_regions(s)
                   if isinstance(r.action, dict) and "muster" in r.action
                   and r.state == RegionState.ENABLED]
        assert musters, "no enabled muster control during a fronted war"
        _press(s, musters[0])
        f0 = war.fronts[0]
        side = (f0.attacker_regiments if war.aggressor == p
                else f0.defender_regiments)
        if side > 0:
            landed = True
            break
    assert landed, "3 muster presses landed no regiment on the front"
    moved = False
    for _ in range(15):
        g.end_turn()
        if war not in g.wars:
            moved = True
            break
        if any(abs(f.line) > 1e-9 for f in war.fronts) \
                or abs(war.war_score) > 1e-9:
            moved = True
            break
    assert moved, "war did not move within 15 turns of mustering"

def test_refusal_classes_drawn():
    s = new_app_state(seed=7)
    g, p = s.game, s.house
    enemy = sorted(h for h in g.houses if h != p)[0]
    declare_war(g, p, enemy, WarGoal(kind="humble"))
    wa = _open_drawer(s)
    decl = {r.action["declare_war"]: r for r in wa
            if isinstance(r.action, dict) and "declare_war" in r.action}
    own = decl.get(p)
    assert own is not None and own.state == RegionState.DISABLED \
        and (own.reason or "").strip(), \
        "own house must be drawn as a refusal with a reason, not omitted"
    at = decl.get(enemy)
    assert at is not None and at.state == RegionState.DISABLED \
        and (at.reason or "").strip(), \
        "an at-war house must be drawn as a refusal with a reason, not omitted"

def test_ai_reaches_a_war_alone():
    for seed in SEEDS:
        g = new_app_state(seed=seed).game
        t = 0
        while t < 40 and not g.wars:
            g.end_turn()
            t += 1
        assert g.wars, f"seed {seed}: no AI war within 40 turns"

def test_letters_carry_no_milestone_tokens():
    for at_war in (False, True):
        s = new_app_state(seed=42)
        g, p = s.game, s.house
        if at_war:
            enemy = sorted(h for h in g.houses if h != p)[0]
            declare_war(g, p, enemy, WarGoal(kind="humble"))
        realm = g.realms[p]
        ex = max((c for c in realm.characters if c.is_alive),
                 key=lambda c: c.age)
        out = " ".join(initiative(g, p, "adjust_garrison", ex))
        assert not re.findall(r"\bG\d+\b", out), out
