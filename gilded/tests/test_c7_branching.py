"""Mission C7, commit 3 - three chains ask the player.

Seed 42, 80 turns. Two runs: one rules every chain petition with its
first option, the other with its second. Each run must rule all three
chain petitions through the docket, and the two runs must produce
different downstream chain beats - at least three chains diverge, and
each ruled chain diverges - the
choice is what changed, not the seed. The chain petition is also drawn on
the House tab as a rule region the player can press.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c7_branching.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gilded.ui.app import new_app_state, _apply_action
from gilded.docket import rule

SEED = 42
TURN_LIMIT = 80
CHAIN_KINDS = {"chain:war_price", "chain:general_strike", "chain:heir_break"}


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


def _run(option_slot):
    s = new_app_state(seed=SEED, start="menu")
    _press_new_game(s)
    g = s.game
    player = next(h for h in sorted(g.houses) if g.houses[h].is_player)
    ruler = g.realms[player].ruler
    ruled_kinds = []
    drawn_region_seen = False
    for _ in range(TURN_LIMIT):
        for p in list(g.docket_by_house.get(player, [])):
            if p.kind.startswith("chain:"):
                # The petition must be drawn on the House tab as a rule
                # region for each option; pressing the region is what
                # rules it (the dispatch spends attention and runs the
                # option's apply, which records the choice on the chain).
                key = p.options[option_slot].key
                s.view.active_tab = "House"
                s.view.draw(s.screen)
                hits = [r for r in s.view.regions._regions
                        if getattr(r, "group", "") == f"petition:{p.pid}"
                        and isinstance(r.action, dict)
                        and r.action.get("rule") == (p.pid, key, None)]
                assert hits, \
                    f"chain petition {p.kind} option {key!r} was not drawn " \
                    "as a rule region on the House tab"
                act = s.view.handle_click(hits[0].rect.center)
                assert act is not None and "rule" in act, \
                    "the chain petition's rule region is not pressable"
                _apply_action(s, act)
                drawn_region_seen = True
                ruled_kinds.append(p.kind)
        g.end_turn()
    assert drawn_region_seen, "no chain petition was drawn as a rule region"
    beats = [(b.turn, b.facet, b.text) for b in g.beats.log
             if b.kind == "chain"]
    gold = g.houses[player].treasury
    return set(ruled_kinds), beats, gold


def test_two_runs_ruling_the_chain_petitions_diverge():
    ruled1, beats1, gold1 = _run(0)
    ruled2, beats2, gold2 = _run(1)
    # All three chains reach the docket in both runs - the heir's stress
    # breaks on seed 42 either way - and each run rules every petition.
    assert len(ruled1 & CHAIN_KINDS) >= 3, \
        f"only {sorted(ruled1 & CHAIN_KINDS)} chains reached the docket"
    assert len(ruled2 & CHAIN_KINDS) >= 3, \
        f"only {sorted(ruled2 & CHAIN_KINDS)} chains reached the docket"
    s1 = {(f, t) for _, f, t in beats1}
    s2 = {(f, t) for _, f, t in beats2}
    only1 = s1 - s2
    only2 = s2 - s1
    assert only1 or only2, "the two rulings produced identical chain beats"
    # Ruling a chain also moves the sim (unrest, stress, treasury), so
    # other chains fire on different beats downstream. At least three
    # chains must diverge between the runs - their later steps were
    # redirected by the choice, not the seed.
    fired = {f for _, f, _ in beats1} | {f for _, f, _ in beats2}
    divergent = []
    for cid in sorted(fired):
        set1 = {t for _, f, t in beats1 if f == cid}
        set2 = {t for _, f, t in beats2 if f == cid}
        if (set1 - set2) or (set2 - set1):
            divergent.append(cid)
    assert len(divergent) >= 3, \
        f"only {sorted(divergent)} chains diverge downstream"
    # And the three chains whose petitions were actually ruled diverge
    # between the runs - the branches the choice selected, not the seed.
    ruled = ruled1 | ruled2
    for cid in sorted(ruled & CHAIN_KINDS):
        facet = cid.removeprefix("chain:")
        set1 = {t for _, f, t in beats1 if f == facet}
        set2 = {t for _, f, t in beats2 if f == facet}
        assert (set1 - set2) or (set2 - set1), \
            f"ruled chain {cid!r} produced identical beats in both runs"
    # The ruling changes the sim: the buyoff option spends treasury gold
    # the crackdown does not, so the two runs end with different gold.
    assert gold1 != gold2, \
        f"both runs ended with the same treasury ({gold1}) - the option " \
        "applies changed nothing measurable"


def test_turn40_house_tab_zero_overlaps(tmp_path, monkeypatch):
    """C6.5 t40 seed-42: the compact petition pass must never draw the
    option buttons onto the bottom bar ("Attention: n" / "Open")."""
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=SEED, start="menu")
    _press_new_game(s)
    g = s.game
    while g.turn < 40:
        g.end_turn()
    s.view.active_tab = "House"
    s.view.draw(s.screen)
    rows = s.view.text_rows
    assert rows, "House tab drew no text rows at t40"
    bad = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a[0].colliderect(b[0]):
                bad.append((a[1][:30], b[1][:30]))
    assert not bad, f"t40 House overlaps: {bad[:5]}"
