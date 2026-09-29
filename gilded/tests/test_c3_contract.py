import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from gilded.ui.app import new_app_state
from gilded import intel

ORDER_FAMILIES = {
    "Combine": ["Organize", "Recognition", "General Strike", "Purge Scabs"],
    "Bank": ["Solvency", "Expansion", "Receivership", "King-making"],
    "Church": ["Endowment", "Crusade of Morals", "Sanctuary", "Schism"],
    "Gazette": ["Circulation War", "Expos\u00e9", "Expose", "Respectability", "Patronage"],
}

def adults(g, house):
    chars = g.realms[house].characters
    it = chars.values() if hasattr(chars, "values") else chars
    return [c for c in it if getattr(c, "age", 0) >= 16]

def test_orders_anatomy_and_goals():
    s = new_app_state(seed=7)
    g = s.game
    g.end_turn()
    assert set(g.orders) == set(ORDER_FAMILIES)
    canon = set(adults(g, s.house)[0].dispositions)
    house_ids = {c.id for h in g.houses for c in adults(g, h)}
    for name, order in g.orders.items():
        assert order.treasury >= 0
        assert isinstance(order.reach, (set, frozenset)) and order.reach
        assert set(order.head.dispositions) == canon
        assert order.head.id not in house_ids
        assert order.goal.family in ORDER_FAMILIES[name]
        assert order.goal.commit_turns == 10

def test_fog_reads_orders():
    s = new_app_state(seed=7)
    g = s.game
    g.end_turn()
    rep = intel.report(g, s.house, "Combine")
    assert rep.tier == 0 and "Their intentions are unknown" in rep.apparent_intent
    g.informants.add((s.house, "Combine"))
    rep = intel.report(g, s.house, "Combine")
    fam = g.orders["Combine"].goal.family
    assert rep.tier >= 2 and f"Pursuing {fam}" in rep.apparent_intent

def test_orders_act_with_faces():
    s = new_app_state(seed=7)
    g = s.game
    faces = {n: set() for n in ORDER_FAMILIES}
    for _ in range(40):
        g.end_turn()
        for n, o in g.orders.items():
            faces[n].add(o.head.name)
    for n in ORDER_FAMILIES:
        hits = [b for b in g.beats.log if b.face in faces[n]
                and (getattr(b, "causes", None) or getattr(b, "provenance", None))]
        assert hits, f"{n} never acted with its head's face in 40 turns"

def test_collision_thwarts_with_deflection():
    for seed in range(3, 19):
        s = new_app_state(seed=seed)
        g = s.game
        for _ in range(16):
            g.end_turn()
            goal = g.orders["Bank"].goal
            if (goal.family == "Receivership" and goal.target in g.houses
                    and goal.target != s.house
                    and goal.opened_turn == g.resolved_turn):
                bank_head = g.orders["Bank"].head.name
                g.set_ambition(s.house, "Buyout", goal.target)
                for _ in range(10):
                    g.end_turn()
                st = g.ambitions.status(s.house)
                assert st["fulfilled"] is False, st
                defl = [b for b in g.beats.log if b.kind == "deflection"
                        and b.face == bank_head
                        and "Receivership" in (b.text or "")
                        and "of 10" in (b.text or "")]
                assert defl, "no deflection beat with the Bank's face"
                return
    raise AssertionError("no seed 3..18 opened a fresh Bank Receivership in 16 turns")

def test_seat_changes_the_game():
    def run(seat):
        s = new_app_state(seed=11)
        if seat:
            s.game.hold_seat(s.house, seat)
        hs = s.game.houses[s.house]
        out = []
        for _ in range(20):
            s.game.end_turn()
            out.append((round(hs.treasury, 6), round(hs.prestige, 6)))
        return out
    control = run(None)
    assert control == run(None), "sim not deterministic"
    for name in ORDER_FAMILIES:
        assert run(name) != control, f"{name} seat changed nothing"
