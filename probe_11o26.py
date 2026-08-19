"""Full attribute comparison: seed-7 Livia/Wei (turn 1, MUST be sellers) vs
seed-47 Atossa/Ashoka (turn 4, must NOT be sellers), plus parent/ruler."""
from gilded.chassis import GildedGame


def describe(ch):
    d = {}
    for k, v in ch.__dict__.items():
        if k in ("_rng", "dispositions", "base_stats", "_society",
                 "age_progress", "focus", "guardian"):
            continue
        if isinstance(v, (str, int, float, bool, type(None))) or isinstance(v, list):
            d[k] = v
    return d


def dump(seed, turns, house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[house]
    ruler = realm.ruler
    print(f"seed={seed} {house} turn={turns}")
    print(f"  RULER {ruler.name} {ruler.id} {describe(ruler)}")
    for ch in realm.characters:
        if ch.id in ruler.children_ids:
            print(f"  KIN   {ch.name} {ch.id} {describe(ch)}")


dump(7, 1, "Ashworth")
dump(47, 4, "Vantrell")
