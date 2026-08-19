import re
from gilded.chassis import GildedGame
import gilded.tests.test_grip as tg

# base behavior: check out what the ORIGINAL rule would return
def base_sellers(realm, ents):
    from gilded.society.realm import DISLOYAL_LOYALTY, DISLOYAL_OPINION, LOYALTY_START
    ruler = realm.ruler
    out = []
    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if not any(ch.id in e.ledger for e in ents):
            continue
        opinion = ch._society.opinions.get((ch.id, ruler.id), 0)
        loyalty = getattr(ch, "loyalty", LOYALTY_START)
        if loyalty < DISLOYAL_LOYALTY or opinion <= DISLOYAL_OPINION:
            out.append(ch)
    return out

# door world t0
g = GildedGame(seed=7)
h = sorted(g.houses)[0]
r = g.realms[h]
print(f"== DOOR seed7 t0 house={h} base_sellers={[c.name for c in base_sellers(r, g.enterprises)]}")
for ch in r.characters:
    if ch.id == r.ruler.id or not ch.is_alive: continue
    holding = sum(e.ledger.get(ch.id, 0) for e in g.enterprises if e.house == h)
    posted = any(v is not None and v.id == ch.id for v in r.court.positions.values())
    print(f"  {ch.name!r} age={ch.age} kin_of_ruler={ch.name.split()[-1]==r.ruler.name.split()[-1]} shares={holding} posted={posted} has_loy={'loyalty' in ch.__dict__ or hasattr(ch,'loyalty')}")

# undivided test world
g2 = tg._game()
h2 = tg._first_house(g2)
r2 = g2.realms[h2]
print(f"\n== UNDIVIDED _game() t0 house={h2} base_sellers={[c.name for c in base_sellers(r2, g2.enterprises)]}")
for ch in r2.characters:
    if ch.id == r2.ruler.id or not ch.is_alive: continue
    holding = sum(e.ledger.get(ch.id, 0) for e in g2.enterprises if e.house == h2)
    posted = any(v is not None and v.id == ch.id for v in r2.court.positions.values())
    print(f"  {ch.name!r} age={ch.age} kin_of_ruler={ch.name.split()[-1]==r2.ruler.name.split()[-1]} shares={holding} posted={posted} has_loy={'loyalty' in ch.__dict__ or hasattr(ch,'loyalty')}")

# what _game is
import inspect
src = inspect.getsource(tg._game)
print("\n_game source:\n", src[:800])
