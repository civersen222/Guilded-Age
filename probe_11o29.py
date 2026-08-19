"""Trace every seller the CURRENT disloyal_shareholders returns for the
live takeover target, per turn, seed 7, 12 turns."""
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

g = GildedGame(seed=7)
for turn in range(12):
    for tk in [t for t in g.takeovers if not t.complete]:
        r = g.realms[tk.target_house]
        sellers = disloyal_shareholders(r, g.enterprises, house_only=False)
        info = []
        for s in sellers:
            loy = getattr(s, "loyalty", None)
            opp = s._society.opinions.get((s.id, r.ruler.id), "NONE")
            unmeas = (loy is None
                      and (s.id, r.ruler.id) not in s._society.opinions)
            shares = sum(e.ledger.get(s.id, 0) for e in g.enterprises
                         if e.house == tk.target_house)
            info.append(f"{s.name}(loy={loy},opp={opp},unmeas={unmeas},"
                        f"sh={shares})")
        print(f"turn {turn} target={tk.target_house}: {info}")
    g.end_turn()

spent = -sum(amt for h in g.houses.values()
             for (_t, l, amt) in h.journal if l == "share purchase")
print(f"total debits: {spent:.1f}")
