import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame

seen = {}

def _run(seed=7, turns=12):
    global seen
    game = GildedGame(seed=seed)
    track = {"calls": 0, "found": 0, "houses": set()}
    orig = realm_mod.disloyal_shareholders
    seen = {}

    def counting(realm, *rest, **kwargs):
        sellers = orig(realm, *rest, **kwargs)
        targets = {tk.target_house for tk in game.takeovers if not tk.complete}
        if realm is not None and getattr(realm, "house_name", None) in targets:
            track["calls"] += 1
            if sellers:
                track["found"] += 1
                track["houses"].add(realm.house_name)
            hn = realm.house_name
            if hn not in seen:
                seen[hn] = []
            seen[hn].append({
                "sellers": [c.name for c in sellers],
                "holders": [
                    (c.name, c.id, c.age, getattr(c, "loyalty", None),
                     c._society.opinions.get((c.id, realm.ruler.id), 0),
                     c.is_alive)
                    for c in realm.characters
                ],
                "ruler": realm.ruler.name,
            })
        return sellers

    realm_mod.disloyal_shareholders = counting
    try:
        for _ in range(turns):
            game.end_turn()
    finally:
        realm_mod.disloyal_shareholders = orig
    return game, track

game, track = _run()
print("track:", track)
print("=== unique target houses & last-state holders ===")
for hn, snaps in seen.items():
    snap = snaps[-1]
    print(f"\n### house={hn} ruler={snap['ruler']}  last sellers={snap['sellers']}")
    for (name, cid, age, loy, opp, alive) in snap["holders"]:
        print(f"  {name:20s} age={age:3} loy={loy} opp={opp} alive={alive}")
