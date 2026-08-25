"""Probe every G2 table assertion the inline self-check does NOT cover."""
from gilded.ui.app import new_app_state

SPEC = {7: "Consolidation", 11: "Glory", 13: "Buyout"}

for seed, fam in SPEC.items():
    s = new_app_state(seed=seed)
    g = s.game
    player = s.house
    rival = next(h for h in sorted(g.houses) if h != player)
    tgt = rival if fam == "Buyout" else None
    g.set_ambition(player, fam, tgt)

    # G2.1b
    g.informants.add((rival, player))
    g.houses[rival].relations[player] = 5
    from gilded import intel
    rep = intel.report(g, rival, player)
    print(f"seed={seed} G2.1b tier={rep.tier} intent_has={f'Pursuing {fam}' in rep.apparent_intent}")

    # G2.2b determinism: second boot
    s2 = new_app_state(seed=seed)
    g2 = s2.game
    p2 = s2.house
    r2 = next(h for h in sorted(g2.houses) if h != p2)
    g2.set_ambition(p2, fam, r2 if fam == "Buyout" else None)
    l1 = sorted((c.id, c.want["text"], c.want["disposition"], c.want["stance"])
                for c in g.realms[player].characters if c.age >= 16)
    l2 = sorted((c.id, c.want["text"], c.want["disposition"], c.want["stance"])
                for c in g2.realms[p2].characters if c.age >= 16)
    print(f"seed={seed} G2.2b deterministic={l1 == l2}")

    st = g.ambitions.status(player)
    for _ in range(10):
        g.end_turn()
    st = g.ambitions.status(player)
    print(f"seed={seed} fulfilled={st['fulfilled']}")
    # G2.3.cause: Cause label in beats.deltas(resolved_turn) contains "ambition"
    goal = g.agendas.get(player)
    # resolution fires on the turn where turn - opened == commit_turns - 1
    # (before the increment), so the credit lands on this turn:
    resolved_turn = goal.opened_turn + goal.commit_turns - 1
    if st["fulfilled"]:
        d = g.beats.deltas(resolved_turn)
        cause_hits = [lbl for lbl, att in d
                      if any("ambition" in str(c) for c in (att.causes or ()))
                      or "ambition" in lbl]
        print(f"seed={seed} G2.3.cause resolved_turn={resolved_turn} "
              f"delta_lines={len(d)} labels={[(l) for l, _ in d]} "
              f"ambition_hits={len(cause_hits)}")
