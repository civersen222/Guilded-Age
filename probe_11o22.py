"""Clean dump of ACTUAL share-holders (in ledger) with relationships.
seed-7 door targets (must have sellers) vs seed-47 Vantrell (must have exactly
1 seller = the grudge holder)."""
from gilded.chassis import GildedGame

DISLOYAL_LOYALTY = 40.0
DISLOYAL_OPINION = -20


def dump(seed, turns, houses):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    for name in houses:
        realm = g.realms[name]
        ruler = realm.ruler
        members = {c.id for c in realm.dynasty.get_all_members()}
        check_ents = [e for e in g.enterprises if e.house == name]
        children_of = {c.id: list(c.children_ids) for c in realm.characters}
        print(f"=== seed={seed} {name} ruler={ruler.name}({ruler.id}) ===")
        for ch in realm.characters:
            if not ch.is_alive or ch.id == ruler.id:
                continue
            holds = {e.name: round(e.ledger.get(ch.id, 0), 1)
                     for e in check_ents if ch.id in e.ledger}
            if not holds:
                continue
            loy = getattr(ch, "loyalty", None)
            opp = ch._society.opinions.get((ch.id, ruler.id), 0)
            unmeas = loy is None and (ch.id, ruler.id) not in ch._society.opinions
            base = (loy is not None and loy < DISLOYAL_LOYALTY
                    or opp <= DISLOYAL_OPINION)
            tags = []
            if ch.id in children_of.get(ruler.id, []):
                tags.append("child")
            if ruler.id in children_of.get(ch.id, []):
                tags.append("parent")
            if not tags:
                tags.append("kin" if ch.id in members else "stranger")
            print(f"  {ch.name[:12]:12s} {ch.id} loy={round(loy,1) if loy is not None else 'None':>5} "
                  f"opp={opp:5.1f} {''.join(tags):8s} "
                  f"unmeas={int(unmeas)} base={int(base)} holds={list(holds)}")


dump(7, 12, ["Ashworth", "Karsgate"])
dump(47, 4, ["Vantrell"])
