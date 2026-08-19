"""Compare unmeasured ruler-children across scenarios: age, gold, is_alive,
spouse, and any other attribute that separates seed-7 sellers from seed-47
non-sellers. Also run the fixture's exact call at turn 4."""
import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame


def kids(seed, turns, house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[house]
    ruler = realm.ruler
    check_ents = [e for e in g.enterprises if e.house == house]
    print(f"seed={seed} {house} ruler={ruler.name}({ruler.id}) age={ruler.age}")
    for ch in realm.characters:
        if ch.id not in ruler.children_ids:
            continue
        holds = {e.name: round(e.ledger.get(ch.id, 0), 1)
                 for e in check_ents if ch.id in e.ledger}
        attrs = {a: getattr(ch, a) for a in ch.__dict__}
        print(f"  child {ch.name[:12]:12s} {ch.id} age={ch.age} alive={ch.is_alive} "
              f"holds={list(holdings) if (holdings := holds) else None}")
        print(f"    attrs: { {k: v for k, v in attrs.items() if k != '_society'} }")


kids(7, 12, "Ashworth")
kids(7, 12, "Karsgate")
kids(47, 4, "Vantrell")
