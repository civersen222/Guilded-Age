"""Trace seed 7 turn by turn: every target house, every holder, door status."""
from gilded.chassis import GildedGame

DISLOYAL_LOYALTY = 40.0
DISLOYAL_OPINION = -20

g = GildedGame(seed=7)
for turn in range(1, 13):
    g.end_turn()
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    if not targets:
        print(f"turn={turn} (no incomplete takeovers)")
        continue
    for name in sorted(targets):
        realm = g.realms[name]
        ruler = realm.ruler
        members = {c.id for c in realm.dynasty.get_all_members()}
        check_ents = [e for e in g.enterprises if e.house == name]
        rows = []
        for ch in realm.characters:
            if not ch.is_alive or ch.id == ruler.id:
                continue
            if not any(ch.id in ent.ledger for ent in check_ents):
                continue
            opinion = ch._society.opinions.get((ch.id, ruler.id), 0)
            loyalty = getattr(ch, "loyalty", None)
            unmeas = loyalty is None and (ch.id, ruler.id) not in ch._society.opinions
            base = (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                    or opinion <= DISLOYAL_OPINION)
            dyn = int(ch.id in members)
            rows.append(f"{ch.name[:14]:14s} loy={round(loyalty,1) if loyalty is not None else 'None'}"
                        f" opp={opinion:5.1f} dyn={dyn} unmeas={int(unmeas)} base={int(base)}")
        print(f"turn={turn} target={name}: " + " | ".join(rows))
