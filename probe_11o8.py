import re
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

g = GildedGame(seed=7)
for turn in range(12):
    targets = sorted({tk.target_house for tk in g.takeovers if not tk.complete})
    for h in targets:
        r = g.realms.get(h)
        if r is None: continue
        ents = [e for e in g.enterprises if e.house == h]
        print(f"t{turn+1} target={h}")
        for ch in r.characters:
            if not ch.is_alive or ch.id == r.ruler.id: continue
            holding = sum(e.ledger.get(ch.id, 0) for e in ents)
            if holding <= 0: continue
            loy = getattr(ch, "loyalty", None)
            op = ch._society.opinions.get((ch.id, r.ruler.id), 0)
            posted = any(v is not None and v.id == ch.id for v in r.court.positions.values()) or any(e.director_id == ch.id for e in ents)
            print(f"    {ch.name!r} age={ch.age} shares={holding} posted={posted} loy={loy} op={op} unmeasured={getattr(ch,'loyalty',None) is None and (ch.id,r.ruler.id) not in ch._society.opinions}")
    g.end_turn()
