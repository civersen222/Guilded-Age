"""Relationship dump: for unmeasured holders, who are they to the ruler?
seed-7 (must be sellers) vs seed-47 (must NOT be sellers)."""
from gilded.chassis import GildedGame


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
            if ch.id not in members:
                continue
            holds = {e.name: round(e.ledger.get(ch.id, 0), 1)
                     for e in check_ents if ch.id in e.ledger}
            if not holds and ch.id != ruler.id:
                continue
            loy = getattr(ch, "loyalty", None)
            tags = []
            if ch.id == ruler.id:
                tags.append("RULER")
            if ch.id in children_of.get(ruler.id, []):
                tags.append("ruler's child")
            if ruler.id in children_of.get(ch.id, []):
                tags.append("ruler's parent")
            if not tags:
                tags.append("other")
            print(f"  {ch.name[:12]:12s} {ch.id} age={ch.age:2d} "
                  f"loy={round(loy,1) if loy is not None else 'None'} "
                  f"{''.join(tags):12s} holds={holds}")


dump(7, 12, ["Ashworth", "Karsgate"])
dump(47, 4, ["Vantrell"])
