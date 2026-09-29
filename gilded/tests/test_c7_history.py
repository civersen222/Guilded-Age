"""Mission C7 wave 4, commit 1 - characters accumulate history.

A seeded 70-turn run at seed 42 must show:
  * >= 60% of the living player-house characters have >= 1 history entry;
  * the ruler has >= 5 history entries;
  * every entry's turn is in [1, game.turn].

Seed 7 is checked with the same three assertions (the gate runs both
seeds). Run EXACTLY as:
    python -m pytest gilded/tests/test_c7_history.py -q
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gilded.ui.app import new_app_state, _apply_action
from gilded import docket

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
    player = [h for h in g.houses if g.houses[h].is_player][0]
    for _ in range(TURNS):
        # gate's exact simulation: rule the FIRST option of every chain
        # petition drawn on the player's docket
        for p in list(g.docket_by_house.get(player, [])):
            if p.kind.startswith("chain:") and p.options:
                docket.rule(g, p, p.options[0].key, g.realms[player].ruler)
        g.end_turn()
    return g


def _assert_history_gate(g):
    player = [h for h in g.houses if g.houses[h].is_player][0]
    realm = g.realms[player]
    living = [c for c in realm.characters if c.is_alive]
    covered = [c for c in living if c.history]
    frac = len(covered) / len(living)
    assert frac >= 0.60, (
        f"{player}: only {len(covered)}/{len(living)} living characters "
        f"({frac:.0%}) carry history")
    ruler = realm.ruler
    assert len(ruler.history) >= 5, (
        f"ruler {ruler.name} has {len(ruler.history)} history entries, "
        f"need >= 5")
    for c in realm.characters:
        for e in c.history:
            assert 1 <= e["turn"] <= g.turn, (
                f"{c.name}: entry at turn {e['turn']} outside "
                f"[1, {g.turn}]")


def test_seed42_history_targets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_history_gate(_run(42))


def test_seed7_history_targets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_history_gate(_run(7))


def test_house_tab_draws_ruler_history(tmp_path, monkeypatch):
    """COMMIT 2: the House tab draws the ruler's last three memory lines —
    the first three words of each drawn entry must appear in a string pygame
    actually rendered while drawing the House tab."""
    monkeypatch.chdir(tmp_path)
    s = new_app_state(seed=42, start="menu")
    _press_new_game(s)
    g = s.game
    for _ in range(TURNS):
        g.end_turn()
    ruler = g.realms[[h for h in g.houses if g.houses[h].is_player][0]].ruler
    entries = [e for e in ruler.history if e["turn"] <= g.turn][-3:]
    assert entries, "ruler has no history to draw"
    s.view.active_tab = "House"
    s.view.draw(s.screen)
    alltext = "\n".join(t for _, t in s.view.text_rows)
    for e in entries:
        words = str(e["text"]).split()[:3]
        needle = " ".join(words)
        assert needle in alltext, \
            f"first three words {needle!r} of entry not rendered on House tab"
