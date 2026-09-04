"""Mission C7, commit 3 - three chains ask the player.

Seed 42, 80 turns. Two runs: one rules every chain petition with its
first option, the other with its second. Each run must rule on at least
two chain petitions through the docket (the other run rules on all three),
and the two runs must produce different downstream chain beats - the
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
                # The petition must be drawable and pressable on the
                # House tab: a rule region for one of its options exists.
                s.view.active_tab = "House"
                s.view.draw(s.screen)
                hits = [r for r in s.view.regions._regions
                        if getattr(r, "group", "") == f"petition:{p.pid}"
                        and isinstance(r.action, dict)
                        and isinstance(r.action.get("rule"), tuple)]
                if hits and not drawn_region_seen:
                    act = s.view.handle_click(hits[0].rect.center)
                    assert act is not None and "rule" in act, \
                        "the chain petition's rule region is not pressable"
                    drawn_region_seen = True
                key = p.options[option_slot].key
                msgs = rule(g, p, key, ruler)
                g.docket_by_house[player].remove(p)
                ruled_kinds.append(p.kind)
        g.end_turn()
    assert drawn_region_seen, "no chain petition was drawn as a rule region"
    beats = [(b.turn, b.facet, b.text) for b in g.beats.log
             if b.kind == "chain"]
    treasury = getattr(g, "treasury", None)
    gold = treasury.gold if treasury is not None else 0
    return set(ruled_kinds), beats, gold


def test_two_runs_ruling_the_chain_petitions_diverge():
    ruled1, beats1, gold1 = _run(0)
    ruled2, beats2, gold2 = _run(1)
    # At least two chains reach the docket in the first-options run;
    # the heir's break only fires once the heir's stress breaks it,
    # which the second-options run's branches cause.
    assert len(ruled1 & CHAIN_KINDS) >= 2, \
        f"only {sorted(ruled1 & CHAIN_KINDS)} chains reached the docket"
    assert len(ruled2 & CHAIN_KINDS) >= 3, \
        f"only {sorted(ruled2 & CHAIN_KINDS)} chains reached the docket"
    s1 = {(f, t) for _, f, t in beats1}
    s2 = {(f, t) for _, f, t in beats2}
    only1 = s1 - s2
    only2 = s2 - s1
    assert only1 or only2, "the two rulings produced identical chain beats"
    # The divergence is in the branches the ruling chose, not noise:
    # each run's unique beats come from chains that were ruled on.
    for facet, text in only1:
        assert facet in {k.removeprefix("chain:") for k in ruled1}, \
            f"divergent beat {facet!r} not from a ruled chain"
    for facet, text in only2:
        assert facet in {k.removeprefix("chain:") for k in ruled2}, \
            f"divergent beat {facet!r} not from a ruled chain"
    # The ruling changes the sim: the buyoff option spends treasury gold
    # the crackdown does not, so the two runs end with different gold.
    assert gold1 != gold2, \
        f"both runs ended with the same treasury ({gold1}) - the option " \
        "applies changed nothing measurable"
