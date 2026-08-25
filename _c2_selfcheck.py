from gilded.ui.app import new_app_state
from gilded.ui import house as ui_house
from gilded import intel
for seed, family in ((7, "Consolidation"), (11, "Glory"), (13, "Buyout")):
    s = new_app_state(seed=seed); g = s.game; player = s.house
    rival = next(h for h in sorted(g.houses) if h != player)
    g.set_ambition(player, family, rival if family == "Buyout" else None)
    goal = g.agendas.get(player)
    assert goal.family == family and goal.commit_turns == 10, goal
    g.informants.add((rival, player)); g.houses[rival].relations[player] = 5
    rep = intel.report(g, rival, player)
    assert rep.tier >= 2 and f"Pursuing {family}" in rep.apparent_intent, rep
    chars = g.realms[player].characters
    it = chars.values() if hasattr(chars, "values") else chars
    adults = [c for c in it if getattr(c, "age", 0) >= 16]
    for c in adults:
        w = c.want
        assert w["text"] and w["disposition"] in c.dispositions
        assert w["stance"] in ("backs", "wary", "opposes"), w
    cards = ui_house.court_cards(g, player)
    assert {card["cid"] for card in cards} == {c.id for c in adults}
    assert ui_house.banner(g, player)["clock"] == "turn 1 of 10"
    for _ in range(3):
        g.end_turn()
    assert ui_house.banner(g, player)["clock"] == "turn 4 of 10"
    st = g.ambitions.status(player)
    assert st["turns_left"] == 7 and st["fulfilled"] is None, st
    for _ in range(7):
        g.end_turn()
    st = g.ambitions.status(player)
    assert st["fulfilled"] in (True, False), st
    assert any("ambition" in (b.text or "").lower() for b in g.beats.log)
    print(seed, family, "fulfilled:", st["fulfilled"])
print("C2 CONTRACT HOLDS")
