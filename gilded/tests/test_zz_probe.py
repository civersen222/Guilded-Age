# C7w3 probe: fixture divergence at seed 5 turn 13 + per-turn secret census.
# TEMPORARY probe file; deleted before the fix commit.
from gilded.chassis import GildedGame


def test_zz_probe_fixture():
    g = GildedGame(seed=5)
    for t in range(1, 14):
        g.end_turn()
        if t in (7, 9, 13):
            print(f"\n=== TURN {t} ===")
            for h in sorted(g.realms):
                for c in g.realms[h].dynasty.all_characters.values():
                    if c.secrets:
                        print(f"  {h} {c.name}: {[(s.description[:40]) for s in c.secrets]}")
    h = "Ferrenholt"
    realm = g.realms[h]
    print(f"\nTURN 13 court {h}:")
    for pos, c in realm.court.positions.items():
        if c is not None:
            print(f"  {pos} = {c.name} base={dict(c.base_stats)} alive={c.is_alive}")
    print(f"ruler {realm.ruler.name} base={dict(realm.ruler.base_stats)} alive={realm.ruler.is_alive}")
