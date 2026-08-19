from gilded.chassis import GildedGame

def dump(seed, turns, target_house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[target_house]
    ruler = realm.ruler
    ents = [e for e in g.enterprises if e.house == target_house]
    dyn_ids = set()
    try:
        for c in realm.dynasty.get_all_members():
            dyn_ids.add(c.id)
    except Exception as e:
        print("dyn err", e)
    print(f"=== seed {seed} t{turns} target {target_house} ruler={ruler.name} dyn_ids={sorted(dyn_ids)} ===")
    for ch in realm.characters:
        if ch.id == ruler.id:
            continue
        shares = [e.ledger.get(ch.id) for e in ents]
        if not any(shares):
            continue
        op = ch._society.opinions.get((ch.id, ruler.id), None)
        loy = getattr(ch, "loyalty", None)
        print(f"  {ch.name} id={ch.id} in_dynasty={ch.id in dyn_ids} shares={shares} op={op} loy={loy}")

dump(7, 4, "Ashworth")
print()
dump(47, 4, "Vantrell")
