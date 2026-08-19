"""Diff the simple (non-dict, non-object) attributes of the unmeasured
ruler-children: seed-47 turn-4 Vantrell (must NOT be sellers) vs seed-7
Ashworth children at the turn-1 firing (MUST be sellers)."""
import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame

SIMPLE = ("age", "is_alive", "is_heir", "is_adult", "gold_reserve",
          "education_track", "graduated", "spouse_id", "parent_id")


def child_attrs(seed, turns, house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[house]
    ruler = realm.ruler
    print(f"seed={seed} {house} turn={turns} ruler_age={ruler.age}")
    for ch in realm.characters:
        if ch.id not in ruler.children_ids:
            continue
        d = {}
        for k, v in ch.__dict__.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                d[k] = v
        print(f"  {ch.name[:12]:12s} {ch.id} {d}")


child_attrs(7, 1, "Ashworth")
child_attrs(7, 2, "Ashworth")
child_attrs(47, 4, "Vantrell")
