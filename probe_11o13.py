from gilded.chassis import GildedGame
from gilded.society.realm import DISLOYAL_LOYALTY, DISLOYAL_OPINION

def dump(seed, turns, target_house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[target_house]
    ruler = realm.ruler
    ents = [e for e in g.enterprises if e.house == target_house]
    print(f"=== seed {seed} t{turns} target {target_house} ruler={ruler.name} ===")
    for ch in realm.characters:
        if ch.id == ruler.id:
            continue
        shares = [e.ledger.get(ch.id) for e in ents]
        if not any(shares):
            continue
        op = ch._society.opinions.get((ch.id, ruler.id), None)
        loy = getattr(ch, "loyalty", None)
        is_heir = getattr(ch, "is_heir", None)
        print(f"  {ch.name} id={ch.id} shares={shares} op={op} loy={loy} heir={is_heir} "
              f"loymark={loy is not None and loy<DISLOYAL_LOYALTY} grudge={op is not None and op<=DISLOYAL_OPINION}")

dump(7, 4, "Ashworth")
print()
dump(47, 4, "Vantrell")
