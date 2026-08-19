from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

def holders(g, h, tag):
    r = g.realms[h]
    ents = [e for e in g.enterprises if e.house == h]
    print(f"== {tag} house={h} turn={g.turn} takeovers={[(t.buyer_house,t.target_house,t.complete) for t in g.takeovers]}")
    print(f"   disloyal_shareholders: {[c.name for c in disloyal_shareholders(r, g.enterprises)]}")
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        has = hasattr(ch, "loyalty")
        op = ch._society.opinions.get((ch.id, r.ruler.id), 0)
        opkey = (ch.id, r.ruler.id) in ch._society.opinions
        holding = sum(e.ledger.get(ch.id, 0) for e in ents)
        print(f"   {ch.name!r} alive={ch.is_alive} age={ch.age} is_heir={getattr(ch,'is_heir',None)} traits={ch.traits} has_loy={has} loy={getattr(ch,'loyalty','<absent>')} op={op} opkey={opkey} shares={holding} stress={getattr(ch,'stress',None)}")

print("### DOOR WORLD seed=7")
g = GildedGame(seed=7)
h = sorted(g.houses)[0]
holders(g, h, "t0")
g.end_turn()
holders(g, h, "t1")

print("### GRIP WORLD seed=14")
g = GildedGame(seed=14)
g.end_turn()
h = sorted(g.houses)[0]
holders(g, h, "t1-after-end_turn")
g2 = GildedGame(seed=14)
holders(g2, sorted(g2.houses)[0], "t0")
