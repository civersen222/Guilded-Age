"""Compare attributes of seed-7 firing sellers (Livia/Wei Ashworth, Thea/Wei
Karsgate) vs seed-47 unmeasured non-sellers (Atossa/Ashoka Vantrell) to find
the separating feature."""
import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame


def char_info(ch, ruler):
    ruler = ch._house.ruler if hasattr(ch, "_house") else None
    d = {}
    for attr in ("id", "name", "is_alive", "loyalty", "spouse_id",
                 "children_ids", "parent_id", "gold_reserve", "age", "role"):
        if hasattr(ch, attr):
            d[attr] = getattr(ch, attr)
    # relationship to ruler
    return d


def dump(seed, turns, houses):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    for name in houses:
        realm = g.realms[name]
        ruler = realm.ruler
        members = {c.id for c in realm.dynasty.get_all_members()}
        check_ents = [e for e in g.enterprises if e.house == name]
        print(f"=== seed={seed} {name} ruler={ruler.name} ===")
        for ch in realm.characters:
            if ch.id in members:
                holds = [e.name for e in check_ents if ch.id in e.ledger]
                d = char_info(ch, ruler)
                print(f"  dyn: {d}")
        for e in check_ents:
            print(f"  ent {e.name}: ledger={ {k: round(v,2) for k,v in e.ledger.items()} }")


dump(7, 12, ["Ashworth", "Karsgate"])
dump(47, 4, ["Vantrell"])
