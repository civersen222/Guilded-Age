"""Replicate the door test's monkeypatch: capture holders at each call site."""
import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame

g = GildedGame(seed=7)
orig = realm_mod.disloyal_shareholders
seen = []

def counting(realm, *rest, **kwargs):
    sellers = orig(realm, *rest, **kwargs)
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    if realm is not None and realm.house_name in targets:
        if sellers:
            ruler = realm.ruler
            members = {c.id for c in realm.dynasty.get_all_members()}
            for s in sellers:
                opinion = s._society.opinions.get((s.id, ruler.id), 0)
                loyalty = getattr(s, "loyalty", None)
                seen.append(f"{realm.house_name} {s.name[:14]:14s} loy={round(loyalty,1) if loyalty is not None else 'None'}"
                            f" opp={opinion:5.1f} dyn={int(s.id in members)}")
    return sellers

realm_mod.disloyal_shareholders = counting
try:
    for _ in range(12):
        g.end_turn()
finally:
    realm_mod.disloyal_shareholders = orig

print(f"{len(seen)} firing calls:")
for row in seen:
    print("  " + row)
