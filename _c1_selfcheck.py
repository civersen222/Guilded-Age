from gilded.ui.app import new_app_state
s = new_app_state(seed=7); g = s.game
mine = [e for e in g.enterprises if e.house == s.house]
g.acts.set_dial(mine[0].eid, 75.0)
assert any(b.kind == "signature" for b in g.beats.log)
for t in range(20):
    g.end_turn()
    lad = g.ladder.standings()
    assert sorted(r for h, r, ax in lad) == list(range(1, len(lad) + 1))
    assert all(att.check(1e-6) for _, att in g.beats.deltas(g.resolved_turn))
kinds = {b.kind for b in g.beats.log}
assert kinds >= {"signature", "season", "inquiry", "deflection"}, kinds
lbl, _ = g.beats.deltas(g.resolved_turn)[0]
att = g.beats.inquire(lbl, g.resolved_turn)
assert att.causes and att.check(1e-6)
from gilded.ui import registry
assert registry.VERBS["set_dial"]["what"]
print("C1 CONTRACT HOLDS")
