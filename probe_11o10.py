import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame

# Run with a wrapper that prints, per advance-triggered call, the sellers + holdings
orig = realm_mod.disloyal_shareholders

g = GildedGame(seed=7)
call_n = [0]
def counting(realm, *rest, **kwargs):
    sellers = orig(realm, *rest, **kwargs)
    call_n[0] += 1
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    if realm is not None and getattr(realm, "house_name", None) in targets:
        h = realm.house_name
        ents = [e for e in g.enterprises if e.house == h]
        # print who holds and their loyalty
        det = []
        for e in ents:
            for cid, amt in e.ledger.items():
                if amt <= 0: continue
                ch = next((c for c in realm.characters if c.id == cid), None)
                if ch is None:
                    det.append(f"  {cid} {amt} OUTSIDER")
                else:
                    loy = getattr(ch, "loyalty", None)
                    det.append(f"  {ch.name} {amt} loy={None if loy is None else round(loy,1)} op={ch._society.opinions.get((ch.id,realm.ruler.id),0)}")
        print(f"CALL {call_n[0]} t={g.turn} target={h} sellers={[c.name for c in sellers]}")
        for d in sorted(det):
            print(d)
    return sellers

realm_mod.disloyal_shareholders = counting
try:
    for _ in range(12):
        g.end_turn()
finally:
    realm_mod.disloyal_shareholders = orig

spent = -sum(amt for h in g.houses.values() for (_t, l, amt) in h.journal if l == "share purchase")
print(f"\nTOTAL share-purchase debits = {spent:.2f}")
