from gilded.chassis import GildedGame
import gilded.society.realm as realm_mod

g = GildedGame(seed=7)
h = sorted(g.houses)[0]
r = g.realms[h]

# find the family holders at t0
fam = []
for ch in r.characters:
    if ch.id == r.ruler.id: continue
    ents = [e for e in g.enterprises if e.house == h]
    if any(ch.id in e.ledger for e in ents):
        fam.append(ch)
print("family holders at t0:", [c.name for c in fam])

orig = realm_mod.disloyal_shareholders
def counting(realm, *rest, **kwargs):
    sellers = orig(realm, *rest, **kwargs)
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    if realm is not None and realm.house_name == h:
        print(f"  advance t={g.turn}: sellers={[c.name for c in sellers]}")
        for c in fam:
            alive = c.is_alive
            loy = getattr(c, "loyalty", None)
            shares = [e.ledger.get(c.id) for e in g.enterprises if e.house == h]
            print(f"    {c.name}: alive={alive} loy={loy} shares={shares}")
    return sellers
realm_mod.disloyal_shareholders = counting

try:
    for i in range(4):
        print(f"--- end_turn {i+1} start ---")
        g.end_turn()
        for c in fam:
            alive = c.is_alive
            loy = getattr(c, "loyalty", None)
            shares = [e.ledger.get(c.id) for e in g.enterprises if e.house == h]
            print(f"after turn {i+1}: {c.name} alive={alive} loy={loy} shares={shares}")
finally:
    realm_mod.disloyal_shareholders = orig
