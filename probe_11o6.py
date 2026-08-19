from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

def dump(g, tag):
    h = sorted(g.houses)[0]
    r = g.realms[h]
    ents = [e for e in g.enterprises if e.house == h]
    print(f"== {tag} house={h} t={g.turn}")
    print(f"   sellers(house_only=False): {[c.name for c in disloyal_shareholders(r, g.enterprises, house_only=False)]}")
    print(f"   sellers(house_only=True):  {[c.name for c in disloyal_shareholders(r, g.enterprises)]}")
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        holding = sum(e.ledger.get(ch.id, 0) for e in ents)
        if holding > 0:
            has = hasattr(ch, "loyalty")
            opkey = (ch.id, r.ruler.id) in ch._society.opinions
            print(f"   HOLDER {ch.name!r} age={ch.age} shares={holding} has_loy={has} opkey={opkey} traits={ch.traits}")

g = GildedGame(seed=7)
dump(g, "door seed7 t0")
print()
g2 = GildedGame(seed=14)
g2.end_turn()
dump(g2, "grip seed14 t1")
print()
g3 = GildedGame(seed=14)
dump(g3, "grip seed14 t0")
print()
g4 = GildedGame()
dump(g4, "undivided default t0")
