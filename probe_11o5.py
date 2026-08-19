from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

g = GildedGame(seed=7)
for t in range(12):
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    for h in sorted(targets):
        r = g.realms[h]
        ents = [e for e in g.enterprises if e.house == h]
        sellers = [c.name for c in disloyal_shareholders(r, g.enterprises)]
        holders = []
        for ch in r.characters:
            if not ch.is_alive or ch.id == r.ruler.id:
                continue
            holding = sum(e.ledger.get(ch.id, 0) for e in ents)
            if holding > 0:
                loy = getattr(ch, "loyalty", "<absent>")
                op = ch._society.opinions.get((ch.id, r.ruler.id), 0)
                opkey = (ch.id, r.ruler.id) in ch._society.opinions
                holders.append(f"{ch.name}({holding:.0f}%,lo={loy},op={op}k={opkey})")
        print(f"t{g.turn} target={h} takeovers={[(x.buyer_house,x.complete) for x in g.takeovers]}")
        print(f"   sellers={sellers}")
        print(f"   holders={holders}")
    g.end_turn()
print("takeovers done:", [(t.buyer_house, t.target_house, t.complete) for t in g.takeovers])
