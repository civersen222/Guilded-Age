"""Instrument Takeover.advance: print what it actually sees during
end_turn, seed 7, 12 turns."""
import gilded.society.schemes as schemes_mod
from gilded.society.realm import disloyal_shareholders
from gilded.chassis import GildedGame

orig = schemes_mod.Takeover.advance
seen = []


def spy(self, realms, enterprises, rng, game):
    r = realms.get(self.target_house)
    if r is not None:
        sellers = disloyal_shareholders(r, enterprises, house_only=False)
        if sellers:
            info = []
            for s in sellers:
                loy = getattr(s, "loyalty", None)
                opp = s._society.opinions.get(
                    (s.id, r.ruler.id), "NONE")
                unmeas = (loy is None
                          and (s.id, r.ruler.id)
                          not in s._society.opinions)
                shares = sum(e.ledger.get(s.id, 0) for e in enterprises
                             if e.house == self.target_house)
                info.append(f"{s.name}(loy={loy},opp={opp},"
                            f"unmeas={unmeas},sh={shares})")
            seen.append((game.turn, self.target_house, self.buyer_house,
                         info))
    return orig(self, realms, enterprises, rng, game)


schemes_mod.Takeover.advance = spy
g = GildedGame(seed=7)
for _ in range(12):
    g.end_turn()
for row in seen:
    print(row)
spent = -sum(amt for h in g.houses.values()
             for (_t, l, amt) in h.journal if l == "share purchase")
print(f"total debits: {spent:.1f}")
