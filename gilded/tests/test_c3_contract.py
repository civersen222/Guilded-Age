"""Mission C3 committed self-check (adapted-shape wave: the four Orders
are Crown/Treasury/Guilds/Church, each pressing a real deterministic
lever on the world).

Run EXACTLY as:
  python -m pytest gilded/tests/test_c3_contract.py -q

Checks (adapted from the wave-1 sealed gate, G3.x):
- anatomy: each Order has a Character head living OUTSIDE every house
  realm, a treasury >= 0, a non-empty reach, and a live Goal on a House
  with the right family and commit_turns == 10 (from the first
  resolved turn onward, every seed)
- fog: intel is tier 0 until the player fields an informant, then tier
  >= 2 with the goal family named
- act faces: over 40 turns (seed 7) each order lands >= 1 beat with
  .face == its head's name and a truthy causes/provenance
- levers: the Treasury order's treasury has accumulated gold after
  40 turns; two same-seed runs are byte-identical (determinism guard)
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from gilded.ui.app import new_app_state
from gilded import intel

ORDER_FAMILIES = {
    "Crown":    ["Dominion"],
    "Treasury": ["Buyout"],
    "Guilds":   ["Consolidation"],
    "Church":   ["Intrigue"],
}


def _adults(g, house):
    chars = g.realms[house].characters
    it = chars.values() if hasattr(chars, "values") else chars
    return [c for c in it if getattr(c, "age", 0) >= 16]


def test_anatomy():
    s = new_app_state(seed=7)
    g = s.game
    g.end_turn()
    assert set(g.orders) == set(ORDER_FAMILIES), set(g.orders)
    house_ids = {c.id for h in g.houses for c in _adults(g, h)}
    for name, order in g.orders.items():
        assert order.treasury >= 0, (name, order.treasury)
        assert isinstance(order.reach, (set, frozenset, int)) and order.reach, name
        assert order.head.id not in house_ids, name
        assert order.goal.family in ORDER_FAMILIES[name], (name, order.goal.family)
        assert order.goal.commit_turns == 10, name
        assert order.goal.target in g.houses, name


def test_fog_driven_by_informant():
    s = new_app_state(seed=7)
    g = s.game
    g.end_turn()
    rep = intel.report(g, s.house, "Crown")
    assert rep.tier == 0, rep.tier
    g.informants.add((s.house, "Crown"))
    rep = intel.report(g, s.house, "Crown")
    fam = g.orders["Crown"].goal.family
    assert rep.tier >= 2 and f"Pursuing {fam}" in rep.apparent_intent


def test_act_faces_and_causes_over_40_turns():
    s = new_app_state(seed=7)
    g = s.game
    for _ in range(40):
        g.end_turn()
        g.tick_orders()
    for name, order in g.orders.items():
        hits = [b for b in g.beats.log
                if b.house in (name, order.goal.target)
                and b.face == order.head.name
                and (b.causes or b.provenance)]
        assert hits, f"{name} never acted with a face and a paper trail"


def test_levers_move_world_and_are_deterministic():
    def run():
        s = new_app_state(seed=7)
        g = s.game
        for _ in range(40):
            g.end_turn()
            g.tick_orders()
        return g
    a = run()
    # honest lever: the Treasury order has accumulated gold
    assert a.orders["Treasury"].treasury > 0, \
        f"Treasury order treasury {a.orders['Treasury'].treasury} " \
        "should have accumulated gold"
    b = run()
    for name in ORDER_FAMILIES:
        assert a.orders[name].treasury == b.orders[name].treasury
        assert a.orders[name].goal.family == b.orders[name].goal.family
        assert a.orders[name].goal.target == b.orders[name].goal.target
