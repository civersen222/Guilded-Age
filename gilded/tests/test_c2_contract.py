"""Mission C2 wave-2 contract, committed as pytest (no shell heredocs).

Two checks:
- boot wants: every adult in EVERY house carries a shape-valid .want
  before any set_ambition, byte-identical across boots of one seed
- grid contract: the wave-1 grid (seeds 7/11/13 x
  Consolidation/Glory/Buyout) end to end: the goal, intel symmetry,
  banner clock, mid/end status, the ambition beat, and
  achievable-and-failable across the grid
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from gilded.intel import report as intel_report
from gilded.ui.app import new_app_state
from gilded.ui import house as ui_house

STANCES = ("backs", "wary", "opposes")
GRID = ((7, "Consolidation"), (11, "Glory"), (13, "Buyout"))


def _adults(g, house):
    chars = g.realms[house].characters
    it = chars.values() if hasattr(chars, "values") else chars
    return [c for c in it if getattr(c, "age", 0) >= 16]


def _want_sig(adults):
    return [(c.id, c.want["text"], c.want["disposition"], c.want["stance"])
            for c in sorted(adults, key=lambda c: c.id)]


# --- boot wants: they exist before any ambition ------------------------

def test_boot_wants_exist_and_deterministic():
    states = [new_app_state(seed=7) for _ in range(2)]
    for s in states:
        g = s.game
        for h in sorted(g.houses):
            adults = _adults(g, h)
            assert adults, f"house {h} has no adults at boot"
            for c in adults:
                w = c.want
                assert w["text"], (h, c.name)
                assert w["disposition"] in c.dispositions
                assert w["stance"] in STANCES
    # the player house's wants are byte-identical across the two boots
    g1, g2 = states[0].game, states[1].game
    player1, player2 = states[0].house, states[1].house
    assert _want_sig(_adults(g1, player1)) == _want_sig(_adults(g2, player2))


# --- the wave-1 grid, ported ------------------------------------------

def test_grid_contract():
    outcomes = {}
    for seed, family in GRID:
        s = new_app_state(seed=seed)
        g = s.game
        player = s.house
        rival = next(h for h in sorted(g.houses) if h != player)
        g.set_ambition(player, family,
                       rival if family == "Buyout" else None)
        goal = g.agendas.get(player)
        assert goal.family == family and goal.commit_turns == 10, goal

        # intel symmetry: the rival reads the stake through UNCHANGED intel
        g.informants.add((rival, player))
        g.houses[rival].relations[player] = 5
        rep = intel_report(g, rival, player)
        assert rep.tier >= 2
        assert f"Pursuing {family}" in rep.apparent_intent

        # the court carries its wants; the cards mirror them
        adults = _adults(g, player)
        for c in adults:
            w = c.want
            assert w["text"] and w["disposition"] in c.dispositions
            assert w["stance"] in STANCES
        cards = ui_house.court_cards(g, player)
        assert {card["cid"] for card in cards} == {c.id for c in adults}

        # the banner's clock
        assert ui_house.banner(g, player)["clock"] == "turn 1 of 10"
        for _ in range(3):
            g.end_turn()
        assert ui_house.banner(g, player)["clock"] == "turn 4 of 10"
        st = g.ambitions.status(player)
        assert st["turns_left"] == 7 and st["fulfilled"] is None, st

        # the window closes: the stake lands one way or the other
        for _ in range(7):
            g.end_turn()
        st = g.ambitions.status(player)
        assert st["fulfilled"] in (True, False), st
        assert any("ambition" in (b.text or "").lower()
                   for b in g.beats.log)
        outcomes[(seed, family)] = bool(st["fulfilled"])

    # the grid is achievable AND failable - not a rubber stamp
    assert True in outcomes.values()
    assert False in outcomes.values()
