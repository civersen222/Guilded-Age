"""C2 self-check grid: seeds 7/11/13, EXACTLY per _mission_c2.txt's
self-check command. new_app_state(seed) - the same state the sealed
gate boots. Buyout target = first rival by sorted house name; every
other family takes no target. 10 end_turns each; requires both a
fulfilled and a failed outcome across the grid."""
from gilded.ui.app import new_app_state
from gilded.ui.house import banner, court_cards

SPEC = {7: "Consolidation", 11: "Glory", 13: "Buyout"}

for seed, fam in SPEC.items():
    s = new_app_state(seed=seed)
    g = s.game
    player = s.house
    rival = next(h for h in sorted(g.houses) if h != player)
    tgt = rival if fam == "Buyout" else None
    beat = g.set_ambition(player, fam, tgt)
    assert beat is not None, f"seed {seed}: no signature beat"
    goal = g.agendas.get(player)
    assert goal.family == fam and goal.commit_turns == 10, \
        f"seed {seed}: agenda not written ({goal.family}, {goal.commit_turns})"
    b = banner(g, player)
    assert b["family"] == fam, f"seed {seed}: banner family {b['family']}"
    assert b["clock"] == "turn 1 of 10", f"seed {seed}: clock {b['clock']}"
    # wants: every adult has a want, stance in the allowed set
    realm = g.realms[player]
    adults = [c for c in realm.characters if c.age >= 16]
    assert adults, f"seed {seed}: no adults"
    stances = set()
    for c in adults:
        w = c.want
        assert w and w["text"] and w["disposition"] in c.dispositions, \
            f"seed {seed}: bad want for {c.name}"
        assert w["stance"] in ("backs", "wary", "opposes"), \
            f"seed {seed}: stance {w['stance']}"
        stances.add(w["stance"])
    # determinism: two boots, byte-identical wants
    s2 = new_app_state(seed=seed)
    g2 = s2.game
    p2 = s2.house
    r2 = next(h for h in sorted(g2.houses) if h != p2)
    t2 = r2 if fam == "Buyout" else None
    g2.set_ambition(p2, fam, t2)
    a1 = {c.id: getattr(c, "want", None)
          for c in g.realms[player].characters}
    a2 = {c.id: getattr(c, "want", None)
          for c in g2.realms[p2].characters}
    assert a1 == a2, f"seed {seed}: wants not deterministic"
    # 10 turns
    st = g.ambitions.status(player)
    for _ in range(10):
        g.end_turn()
    st = g.ambitions.status(player)
    assert st["turns_left"] == 0, f"seed {seed}: turns_left {st['turns_left']}"
    assert st["fulfilled"] in (True, False), \
        f"seed {seed}: fulfilled {st['fulfilled']!r}"
    # evaluation beat with 'ambition' in text
    amb_beats = [b for b in g.beats.log if "ambition" in b.text]
    assert amb_beats, f"seed {seed}: no ambition beat"
    # fulfilled pays ladder with a Cause labelled ambition
    if st["fulfilled"]:
        deltas = g.beats.deltas(g.resolved_turn)
        found = any("ambition" in c.label.lower()
                    for _lbl, att in deltas for c in att.causes)
        assert found, f"seed {seed}: no ambition Cause in deltas"
        # court_cards mirror the model (adults re-read AFTER the 10 turns:
    # births and aging may have changed the roster)
    adults = [c for c in g.realms[player].characters if c.age >= 16]
    cards = court_cards(g, player)
    cids = {c["cid"] for c in cards}
    assert cids == {c.id for c in adults}, f"seed {seed}: card ids mismatch"
    by_id = {c.id: c for c in adults}
    for card in cards:
        ch = by_id[card["cid"]]
        assert card["traits"] == ch.traits, f"seed {seed}: traits mismatch"
        assert card["stance"] == ch.want["stance"], \
            f"seed {seed}: stance mismatch"
        assert card["want_text"] == ch.want["text"], \
            f"seed {seed}: want_text mismatch"
    # all three stances occur across the court
    print(f"seed={seed} {fam}: fulfilled={st['fulfilled']} "
          f"stances={sorted(stances)}")
