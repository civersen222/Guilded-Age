from gilded.chassis import GildedGame

def dump(seed, turns, target_house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[target_house]
    ruler = realm.ruler
    ents = [e for e in g.enterprises if e.house == target_house]
    print(f"=== seed {seed} t{turns} target {target_house} ===")
    for ch in realm.characters:
        if ch.id == ruler.id:
            continue
        shares = [e.ledger.get(ch.id) for e in ents]
        if not any(shares):
            continue
        d = ch.__dict__
        rel = {k: v for k, v in d.items() if not k.startswith("_") and not isinstance(v, (dict, list, set))}
        print(f"  {ch.name} id={ch.id} shares={shares}")
        print(f"    {rel}")

dump(7, 4, "Ashworth")
print()
dump(47, 4, "Vantrell")
