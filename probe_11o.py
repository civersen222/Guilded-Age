import gilded.society.realm as realm
from gilded.chassis import GildedGame
import gilded.society.schemes as schemes

DISLOYAL_LOYALTY = 40.0

def _label_debits(game, label):
    return -sum(amt for h in game.houses.values()
                for (_t, l, amt) in h.journal if l == label)

def mk(fn):
    def counting(r, *a, **k):
        if r is None:
            return realm.disloyal_shareholders(r, *a, **k)
        return fn(r, a[0] if a else k.get("enterprises", []), **{})
    return counting

def base_list(r, ents):
    out = []
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        if not any(ch.id in e.ledger for e in ents): continue
        opinion = ch._society.opinions.get((ch.id, r.ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        if (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                or opinion <= -20):
            out.append(ch)
    return out

def rule_C(r, ents):
    out = []
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        if not any(ch.id in e.ledger for e in ents): continue
        opinion = ch._society.opinions.get((ch.id, r.ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        if (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                or opinion <= -10):
            out.append(ch)
    return out

def rule_B(r, ents):
    out = []
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        if not any(ch.id in e.ledger for e in ents): continue
        opinion = ch._society.opinions.get((ch.id, r.ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        if loyalty is None or (loyalty is not None and loyalty < DISLOYAL_LOYALTY) or opinion <= -20:
            out.append(ch)
    return out

def run(name, fn, turns=12):
    game = GildedGame(seed=7)
    schemes.disloyal_shareholders = mk(fn)
    for _ in range(turns):
        game.end_turn()
    schemes.disloyal_shareholders = realm.disloyal_shareholders
    print(f"{name}: spent={_label_debits(game, 'share purchase'):.1f}")

for name, fn in [("base", base_list), ("C op<=-10", rule_C), ("B None=seller", rule_B)]:
    run(name, fn)
